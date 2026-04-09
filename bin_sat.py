import json
import math
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

from pysat.card import CardEnc, EncType
from pysat.formula import CNF, IDPool
from pysat.pb import PBEnc
from pysat.solvers import Solver


@dataclass
class SatSolveResult:
    feasible: bool
    build_time_us: float
    solve_time_us: float
    total_time_us: float
    k: int
    assignment: Optional[Dict[Any, int]] = None


@dataclass
class SatOptimizationResult:
    feasible: bool
    optimal_bins: Optional[int]
    build_time_us: float
    solve_time_us: float
    total_time_us: float
    assignment: Optional[Dict[Any, int]] = None


class BinPackingSAT:
    """
    SAT solver for bin packing.

    Important design choice:
    - We read items, sizes, and capacity information from the JSON.
    - We do NOT treat the JSON 'bins' list as a hard upper bound.
    - Instead, we generate candidate bins internally, up to num_items,
      which is always a safe upper bound if every item fits alone.
    """

    def __init__(self, json_path: str):
        self.json_path = json_path
        self.instance = self._load_instance(json_path)

        self.items = self.instance["items"]
        self.sizes = self.instance["sizes"]
        self.bin_capacity = self.instance["bin_capacity"]

        self.num_items = len(self.items)

        # Safe candidate bins: one per item
        self.candidate_bins = list(range(self.num_items))

        # Sanity check: each item must fit alone in one bin
        too_large = [i for i in self.items if self.sizes[i] > self.bin_capacity]
        if too_large:
            raise ValueError(
                f"Some items do not fit into a single bin of capacity {self.bin_capacity}: {too_large}"
            )

    @staticmethod
    def _load_instance(json_path: str) -> Dict:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = data["sets"]["items"]
        raw_sizes = data["parameters"]["size"]
        raw_capacities = data["parameters"]["capacity"]

        sizes = BinPackingSAT._normalize_parameter(items, raw_sizes)

        # We assume identical bin capacities within one instance.
        # If the JSON contains a list, we read the first one and verify uniformity.
        if isinstance(raw_capacities, list):
            if len(raw_capacities) == 0:
                raise ValueError("Capacity list is empty.")
            first_cap = int(raw_capacities[0])
            if any(int(c) != first_cap for c in raw_capacities):
                raise ValueError(
                    "This SAT version assumes identical bin capacities within an instance."
                )
            bin_capacity = first_cap
        elif isinstance(raw_capacities, dict):
            vals = [int(v) for v in raw_capacities.values()]
            if len(vals) == 0:
                raise ValueError("Capacity dict is empty.")
            first_cap = vals[0]
            if any(v != first_cap for v in vals):
                raise ValueError(
                    "This SAT version assumes identical bin capacities within an instance."
                )
            bin_capacity = first_cap
        elif isinstance(raw_capacities, int):
            bin_capacity = int(raw_capacities)
        else:
            raise ValueError(f"Unsupported capacity format: {type(raw_capacities)}")

        return {
            "items": items,
            "sizes": sizes,
            "bin_capacity": bin_capacity,
        }

    @staticmethod
    def _normalize_parameter(keys, raw_value):
        if isinstance(raw_value, dict):
            return {k: int(v) for k, v in raw_value.items()}

        if isinstance(raw_value, list):
            if len(raw_value) != len(keys):
                raise ValueError("Parameter list length does not match keys length.")
            return {k: int(v) for k, v in zip(keys, raw_value)}

        if isinstance(raw_value, int):
            return {k: int(raw_value) for k in keys}

        raise ValueError(f"Unsupported parameter format: {type(raw_value)}")

    def lower_bound(self) -> int:
        total_size = sum(self.sizes[i] for i in self.items)
        return max(1, math.ceil(total_size / self.bin_capacity))

    def upper_bound(self) -> int:
        # Safe upper bound: one bin per item
        return self.num_items

    def _x_var(self, vpool: IDPool, item, bin_id: int) -> int:
        return vpool.id(f"x[{item},{bin_id}]")

    def build_cnf_for_k(self, k: int) -> Tuple[CNF, IDPool, List[int], float]:
        """
        Build CNF for:
            'Can the items be packed into at most k bins?'
        using the first k internally generated candidate bins.
        """
        if not (1 <= k <= self.num_items):
            raise ValueError(f"k must be in [1, {self.num_items}], got {k}")

        start = time.perf_counter()

        cnf = CNF()
        vpool = IDPool()

        allowed_bins = self.candidate_bins[:k]

        # Symmetry breaking: put the first item in the first bin
        first_item = self.items[0]
        cnf.append([self._x_var(vpool, first_item, allowed_bins[0])])

        # Exactly one bin per item
        for item in self.items:
            lits = [self._x_var(vpool, item, b) for b in allowed_bins]
            eq1 = CardEnc.equals(
                lits=lits,
                bound=1,
                vpool=vpool,
                encoding=EncType.seqcounter,
            )
            cnf.extend(eq1.clauses)

        # Capacity constraint for each bin
        for b in allowed_bins:
            lits = [self._x_var(vpool, item, b) for item in self.items]
            weights = [self.sizes[item] for item in self.items]

            pb = PBEnc.leq(
                lits=lits,
                weights=weights,
                bound=self.bin_capacity,
                vpool=vpool,
            )
            cnf.extend(pb.clauses)

        end = time.perf_counter()
        build_time_us = (end - start) * 1e6

        return cnf, vpool, allowed_bins, build_time_us

    def solve_for_k(self, k: int, solver_name: str = "glucose4") -> SatSolveResult:
        cnf, vpool, allowed_bins, build_time_us = self.build_cnf_for_k(k)

        start = time.perf_counter()
        with Solver(name=solver_name, bootstrap_with=cnf.clauses) as solver:
            feasible = solver.solve()
            model = solver.get_model() if feasible else None
        end = time.perf_counter()

        solve_time_us = (end - start) * 1e6
        total_time_us = build_time_us + solve_time_us

        assignment = None
        if feasible and model is not None:
            assignment = self._decode_assignment(model, vpool, allowed_bins)

        return SatSolveResult(
            feasible=feasible,
            build_time_us=build_time_us,
            solve_time_us=solve_time_us,
            total_time_us=total_time_us,
            k=k,
            assignment=assignment,
        )

    def _decode_assignment(
        self, model: List[int], vpool: IDPool, allowed_bins: List[int]
    ) -> Dict[Any, int]:
        model_set = {lit for lit in model if lit > 0}
        assignment: Dict[Any, int] = {}

        for item in self.items:
            for b in allowed_bins:
                var = self._x_var(vpool, item, b)
                if var in model_set:
                    assignment[item] = b
                    break

        return assignment

    def solve_optimally(self, solver_name: str = "glucose4") -> SatOptimizationResult:
        lb = self.lower_bound()
        ub = self.upper_bound()

        total_build_time_us = 0.0
        total_solve_time_us = 0.0
        best_assignment = None

        while lb < ub:
            k = (lb + ub) // 2
            result = self.solve_for_k(k, solver_name=solver_name)

            total_build_time_us += result.build_time_us
            total_solve_time_us += result.solve_time_us

            if result.feasible:
                ub = k
                best_assignment = result.assignment
            else:
                lb = k + 1

        final_result = self.solve_for_k(lb, solver_name=solver_name)
        total_build_time_us += final_result.build_time_us
        total_solve_time_us += final_result.solve_time_us

        if not final_result.feasible:
            return SatOptimizationResult(
                feasible=False,
                optimal_bins=None,
                build_time_us=total_build_time_us,
                solve_time_us=total_solve_time_us,
                total_time_us=total_build_time_us + total_solve_time_us,
                assignment=None,
            )

        if final_result.assignment is not None:
            best_assignment = final_result.assignment

        return SatOptimizationResult(
            feasible=True,
            optimal_bins=lb,
            build_time_us=total_build_time_us,
            solve_time_us=total_solve_time_us,
            total_time_us=total_build_time_us + total_solve_time_us,
            assignment=best_assignment,
        )

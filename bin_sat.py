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
    assignment: Optional[Dict[Any, Any]] = None


@dataclass
class SatOptimizationResult:
    feasible: bool
    optimal_bins: Optional[int]
    build_time_us: float
    solve_time_us: float
    total_time_us: float
    assignment: Optional[Dict[Any, Any]] = None


class BinPackingSAT:
    """
    SAT solver for the decision version of bin packing:
        'Can the items be packed into at most K bins?'

    Then uses binary search on K to find the optimum.
    """

    def __init__(self, json_path: str):
        self.json_path = json_path
        self.instance = self._load_instance(json_path)

        self.items = self.instance["items"]
        self.bins = self.instance["bins"]
        self.sizes = self.instance["sizes"]
        self.capacities = self.instance["capacities"]

        self.num_items = len(self.items)
        self.num_bins = len(self.bins)

    @staticmethod
    def _load_instance(json_path: str) -> Dict:
        """
        Expected JSON structure:
        {
            "sets": {
                "items": [...],
                "bins": [...]
            },
            "parameters": {
                "size": {...} or [...],
                "capacity": {...} or [...] or scalar
            }
        }
        """
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = data["sets"]["items"]
        bins = data["sets"]["bins"]

        raw_sizes = data["parameters"]["size"]
        raw_capacities = data["parameters"]["capacity"]

        sizes = BinPackingSAT._normalize_parameter(items, raw_sizes)
        capacities = BinPackingSAT._normalize_parameter(bins, raw_capacities)

        return {
            "items": items,
            "bins": bins,
            "sizes": sizes,
            "capacities": capacities,
        }

    @staticmethod
    def _normalize_parameter(keys, raw_value):
        """
        Supports:
        - dict form: {key: value, ...}
        - list form:  [v1, v2, ...] matched in order with keys
        - scalar form: c, replicated for all keys
        """
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
        max_capacity = max(self.capacities[b] for b in self.bins)
        return max(1, math.ceil(total_size / max_capacity))

    def upper_bound(self) -> int:
        return self.num_bins

    def _x_var(self, vpool: IDPool, item, bin_name) -> int:
        return vpool.id(f"x[{item},{bin_name}]")

    def build_cnf_for_k(self, k: int) -> Tuple[CNF, IDPool, List[Any]]:
        """
        Build CNF for the decision problem:
            'Is there a packing using at most the first k bins?'
        """
        if not (1 <= k <= self.num_bins):
            raise ValueError(f"k must be in [1, {self.num_bins}], got {k}")

        start = time.perf_counter()

        cnf = CNF()
        vpool = IDPool()

        allowed_bins = self.bins[:k]

        # Symmetry breaking: put the first item in the first allowed bin.
        first_item = self.items[0]
        first_bin = allowed_bins[0]
        cnf.append([self._x_var(vpool, first_item, first_bin)])

        # Each item must be assigned to exactly one of the first k bins.
        for item in self.items:
            lits = [self._x_var(vpool, item, b) for b in allowed_bins]

            eq1 = CardEnc.equals(
                lits=lits,
                bound=1,
                vpool=vpool,
                encoding=EncType.seqcounter,
            )
            cnf.extend(eq1.clauses)

        # Capacity constraint for each bin:
        # sum_i size_i * x[i,j] <= capacity[j]
        for b in allowed_bins:
            lits = [self._x_var(vpool, item, b) for item in self.items]
            weights = [self.sizes[item] for item in self.items]
            capacity = self.capacities[b]

            pb = PBEnc.leq(
                lits=lits,
                weights=weights,
                bound=capacity,
                vpool=vpool,
            )
            cnf.extend(pb.clauses)

        end = time.perf_counter()
        build_time_us = (end - start) * 1e6

        cnf._build_time_us = build_time_us
        return cnf, vpool, allowed_bins

    def solve_for_k(self, k: int, solver_name: str = "glucose4") -> SatSolveResult:
        """
        Solve the decision problem for a fixed k.
        """
        cnf, vpool, allowed_bins = self.build_cnf_for_k(k)
        build_time_us = getattr(cnf, "_build_time_us", 0.0)

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
        self, model: List[int], vpool: IDPool, allowed_bins: List[Any]
    ) -> Dict[Any, Any]:
        """
        Decode item -> bin assignment from a satisfying model.
        """
        model_set = {lit for lit in model if lit > 0}
        assignment: Dict[Any, Any] = {}

        for item in self.items:
            for b in allowed_bins:
                var = self._x_var(vpool, item, b)
                if var in model_set:
                    assignment[item] = b
                    break

        return assignment

    def solve_optimally(self, solver_name: str = "glucose4") -> SatOptimizationResult:
        """
        Binary search on k to find the minimum number of bins.
        Measures the total build/solve time accumulated across all SAT calls.

        If the instance is infeasible even when all available bins are allowed,
        returns feasible=False instead of crashing.
        """
        lb = self.lower_bound()
        ub = self.upper_bound()

        total_build_time_us = 0.0
        total_solve_time_us = 0.0
        best_assignment = None

        # Immediate infeasibility from simple capacity lower bound.
        if lb > ub:
            return SatOptimizationResult(
                feasible=False,
                optimal_bins=None,
                build_time_us=0.0,
                solve_time_us=0.0,
                total_time_us=0.0,
                assignment=None,
            )

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

        # Final solve at k = lb = ub.
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

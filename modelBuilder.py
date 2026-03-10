from pyscipopt import Model, quicksum
from itertools import product
import json


class ModelBuilder:

    def __init__(self, json_file):
        with open(json_file) as f:
            self.data = json.load(f)
        self.model = Model(self.data.get("name", "model"))
        self.sets = self.data.get("sets", {})
        self.parameters = self.data.get("parameters", {})
        self.variables = {}

    def build_variables(self):
        for v in self.data["variables"]:
            name = v["name"]
            sets = v.get("sets", [])
            vtype = self.map_type(v["type"])
            if not sets:
                self.variables[name] = self.model.addVar(name=name, vtype=vtype)
                continue
            self.variables[name] = {}
            index_sets = [self.sets[s] for s in sets]
            for idx in product(*index_sets):
                self.variables[name][idx] = self.model.addVar(name=f"{name}{idx}", vtype=vtype)

    def parse_expr(self, expr, env):
        # This handles literal numbers (like the number 1)
        if isinstance(expr, (int, float)):
            return expr

        # --- FIX IS HERE ---
        if "var" in expr:
            name = expr["var"]
            indices = expr.get("index", [])
            # For each index, check if it's a loop variable (in env) or a literal int
            idx_tuple = tuple(env[i] if i in env else int(i) for i in indices)
            return self.variables[name][idx_tuple]

        # --- AND FIX IS HERE ---
        if "param" in expr:
            name = expr["param"]
            indices = expr.get("index", [])
            if not indices:
                return self.parameters.get(name)  # Can be a single value parameter
            # For each index, check if it's a loop variable (in env) or a literal int
            # Bin packing only uses one index for params, but this is more robust
            idx_tuple = tuple(env[i] if i in env else int(i) for i in indices)
            return self.parameters[name][idx_tuple[0]]  # Access parameter list with the first index

        if "sum" in expr:
            s = expr["sum"]
            idx = s["index"]
            setname = s["set"]
            values = []
            for val in self.sets[setname]:
                new_env = env.copy()
                new_env[idx] = val
                values.append(self.parse_expr(s["expr"], new_env))
            return quicksum(values)

        if "mul" in expr:
            result = 1
            for part in expr["mul"]:
                result *= self.parse_expr(part, env)
            return result

        if "add" in expr:  # Added for completeness
            result = 0
            for part in expr["add"]:
                result += self.parse_expr(part, env)
            return result

        raise Exception(f"Unknown expression: {expr}")

    def build_constraints(self):
        for c in self.data["constraints"]:
            if "forall" in c:
                idx = c["forall"]["index"]
                setname = c["forall"]["set"]
                for val in self.sets[setname]:
                    env = {idx: val}
                    self.add_constraint(c["expr"], env)
            else:
                self.add_constraint(c["expr"], {})

    def add_constraint(self, expr, env):
        left = self.parse_expr(expr["left"], env)
        right = self.parse_expr(expr["right"], env)
        op = expr["op"]
        if op == "==":
            self.model.addCons(left == right)
        elif op == "<=":
            self.model.addCons(left <= right)
        elif op == ">=":
            self.model.addCons(left >= right)

    def build_objective(self):
        obj_data = self.data.get("objective")
        if not obj_data: return
        obj_expr = self.parse_expr(obj_data["expr"], {})
        sense = obj_data["sense"]
        self.model.setObjective(obj_expr, sense)

    def map_type(self, t):
        return {"binary": "B", "integer": "I", "continuous": "C"}[t]

    def build(self):
        self.build_variables()
        self.build_objective()
        self.build_constraints()
        return self.model
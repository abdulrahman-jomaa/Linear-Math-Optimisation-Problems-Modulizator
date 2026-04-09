import csv

from bin_sat import BinPackingSAT

PROBLEMS_PATH = ["p1.json", "p2.json", "p3.json"]
REPETITIONS = 1  # keep 1 for testing first


def write_to_csv(problem_index: int, rows):
    filename = f"Data_P{problem_index}.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


if __name__ == "__main__":
    print("Starting SAT experiment...")

    for idx, problem_path in enumerate(PROBLEMS_PATH, start=1):
        rows = [["Optimal Bins", "Solving Time", "Building Time", "Total Time"]]

        for _ in range(REPETITIONS):
            solver = BinPackingSAT(problem_path)
            result = solver.solve_optimally(solver_name="glucose4")

            rows.append(
                [
                    result.optimal_bins if result.feasible else "INFEASIBLE",
                    result.solve_time_us,
                    result.build_time_us,
                    result.total_time_us,
                ]
            )

        write_to_csv(idx, rows)
        print(f"Problem {problem_path} done.")

    print("Saved all SAT data in csv files.")

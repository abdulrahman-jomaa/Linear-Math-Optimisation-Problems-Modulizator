from src.modelBuilder import ModelBuilder
from bin_sat import BinPackingSAT
import time
import csv
import os
from colorama import Fore

REPETITIONS = 1


def write_to_csv(data):
    """
    Expected order in data:
    [m1_p1, m1_p2, m1_p3, m2_p1, m2_p2, m2_p3, sat_p1, sat_p2, sat_p3]
    """
    os.makedirs("Data", exist_ok=True)

    labels = [
        ("m1", 1),
        ("m1", 2),
        ("m1", 3),
        ("m2", 1),
        ("m2", 2),
        ("m2", 3),
        ("sat", 1),
        ("sat", 2),
        ("sat", 3),
    ]

    for matrix, (method, problem_idx) in zip(data, labels):
        filename = f"Data/Data_{method}_P{problem_idx}.csv"
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(matrix)


if __name__ == "__main__":
    elapsed_times_4_all_problems = []

    print(Fore.RED + "Starting the experiment :\n")

    # -----------------------------------
    # m1 and m2 formulations with SCIP
    # -----------------------------------
    problems_path = ["p1.json", "p2.json", "p3.json"]
    formulations_path = ["m1_", "m2_"]

    # for m_path in formulations_path:
    #     print(Fore.RED + f"Working on problems with : {m_path}\n")

    #     for p_path in problems_path:
    #         path = "problems/" + m_path + p_path
    #         m = [["Solving Time", "Building Time", "Total Time"]]

    #         print(Fore.WHITE + f"Started problem : {m_path}{p_path}\n")

    #         for _ in range(REPETITIONS):
    #             # building time
    #             start = time.perf_counter()
    #             model = ModelBuilder(path).build()
    #             end = time.perf_counter()
    #             building_elapsed_time_us = (end - start) * 1e6

    #             # solving time
    #             start = time.perf_counter()
    #             model.optimize()
    #             end = time.perf_counter()
    #             solving_elapsed_time_us = (end - start) * 1e6

    #             m.append(
    #                 [
    #                     solving_elapsed_time_us,
    #                     building_elapsed_time_us,
    #                     building_elapsed_time_us + solving_elapsed_time_us,
    #                 ]
    #             )

    #         elapsed_times_4_all_problems.append(m)
    #         print(Fore.RED + f"Problem {m_path}{p_path} done.\n")

    # -----------------------------------
    # SAT formulation with PySAT
    # -----------------------------------
    sat_problems_path = ["sat_p1.json", "sat_p2.json", "sat_p3.json"]

    print(Fore.RED + "Working on problems with : SAT\n")

    for sat_p in sat_problems_path:
        path = "problems/" + sat_p
        m = [["Solving Time", "Building Time", "Total Time"]]

        print(Fore.WHITE + f"Started SAT problem : {sat_p}\n")

        for _ in range(REPETITIONS):
            solver = BinPackingSAT(path)
            result = solver.solve_optimally(solver_name="glucose4")

            m.append(
                [
                    result.optimal_bins if result.feasible else "INFEASIBLE",
                    result.solve_time_us,
                    result.build_time_us,
                    result.total_time_us,
                ]
            )

        elapsed_times_4_all_problems.append(m)
        print(Fore.RED + f"SAT Problem {sat_p} done.\n")

    write_to_csv(elapsed_times_4_all_problems)
    print(Fore.RED + "Saved All data in csv files.\n")

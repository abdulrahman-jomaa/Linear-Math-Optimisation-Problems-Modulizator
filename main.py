from src.modelBuilder import ModelBuilder
import time
import csv
from colorama import Fore

REPETITIONS = 1


def write_to_csv(data):
    j = 0
    i = 0
    for matrix in data:
        filename = f"Data/Data_m{j + 1}_P{i + 1}.csv"

        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(matrix)

        if i == 2:
            j += 1
            i = 0
            continue
        i += 1


if __name__ == "__main__":
    problems_path = ["p1.json", "p2.json", "p3.json"]
    formulations_path = ["m1_", "m2_"]
    elapsed_times_4_all_problems = []

    print(Fore.RED + "Starting the experiment : \n")

    for m_path in formulations_path:

        print(Fore.RED + "Working on problems with : " + m_path + "\n")

        for p_path in problems_path:
            path = "problems/" + m_path + p_path
            m = [["Solving Time", "Building Time", "Total Time"]]

            print(Fore.WHITE + "Started problem : " + m_path + p_path + "\n")
            for _ in range(REPETITIONS):
                # building time
                start = time.perf_counter()
                model = ModelBuilder(path).build()
                end = time.perf_counter()
                building_elapsed_time_us = (end - start) * 1e6

                # model.hideOutput()

                # solving time
                start = time.perf_counter()
                model.optimize()
                end = time.perf_counter()

                solving_elapsed_time_us = (end - start) * 1e6
                m.append(
                    [
                        solving_elapsed_time_us,
                        building_elapsed_time_us,
                        building_elapsed_time_us + solving_elapsed_time_us,
                    ]
                )

            elapsed_times_4_all_problems.append(m)

            print(Fore.RED + "Problem " + m_path + p_path + " done.\n")

    write_to_csv(elapsed_times_4_all_problems)
    print(Fore.RED + "Saved All data in csv files.\n")

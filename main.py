from modelBuilder import ModelBuilder
import time
import csv


def write_to_csv(data):
    for i, matrix in enumerate(data):
        filename = f"Data_P{i + 1}.csv"

        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(matrix)


if __name__ == '__main__':
    problems_path = ["p1.json", "p2.json", "p3.json"]
    REPETITIONS = 200
    elapsed_times_4_all_problems = []

    print("Starting the experiment : ")

    for p_path in problems_path:
        m = [["Solving Time", "Building Time", "Total Time"]]
        for _ in range(REPETITIONS):
            # building time
            start = time.perf_counter()
            model = ModelBuilder(p_path).build()
            end = time.perf_counter()
            building_elapsed_time_us = (end - start) * 1e6

            model.hideOutput()

            # solving time
            start = time.perf_counter()
            model.optimize()
            end = time.perf_counter()

            solving_elapsed_time_us = (end - start) * 1e6
            m.append([solving_elapsed_time_us, building_elapsed_time_us,
                      building_elapsed_time_us + solving_elapsed_time_us])

        elapsed_times_4_all_problems.append(m)

        print("Problem " + p_path + " done.")

    write_to_csv(elapsed_times_4_all_problems)
    print("Saved All data in csv files.")

from src.modelBuilder import ModelBuilder
from bin_sat import BinPackingSAT
import time
import csv
import os
from colorama import Fore
import multiprocessing as mp
from queue import Empty

REPETITIONS = 1
TIME_LIMIT_SECONDS = 60
TIMEOUT_LABEL = f"{TIME_LIMIT_SECONDS}s+"


def write_to_csv(data):
    """
    Expected order in data:
    [m1_p3, m2_p3, sat_p3]
    """
    os.makedirs("Data", exist_ok=True)

    labels = [
        ("m1", 3),
        ("m2", 3),
        ("sat", 3),
    ]

    for matrix, (method, problem_idx) in zip(data, labels):
        filename = f"Data/Data_{method}_P{problem_idx}.csv"
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(matrix)


def write_sat_solution_to_csv(
    assignment, sizes, capacity, filename="Data/Data_sat_P3_solution.csv"
):
    """
    Writes the SAT assignment in a CSV file.

    Columns:
    Bin, Item, Size, Bin Load, Remaining Capacity
    """
    os.makedirs("Data", exist_ok=True)

    if assignment is None:
        return

    # Compute total load of each bin
    bin_loads = {}

    for item, bin_id in assignment.items():
        bin_loads.setdefault(bin_id, 0)
        bin_loads[bin_id] += sizes[item]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow(["Bin", "Item", "Size", "Bin Load", "Remaining Capacity"])

        # Sort by bin, then by item
        rows = sorted(assignment.items(), key=lambda x: (x[1], x[0]))

        for item, bin_id in rows:
            load = bin_loads[bin_id]
            remaining = capacity - load

            writer.writerow([bin_id, item, sizes[item], load, remaining])


def run_mip_instance(path, queue):
    try:
        # building time
        start = time.perf_counter()
        model = ModelBuilder(path).build()
        model.hideOutput()
        end = time.perf_counter()
        building_elapsed_time_us = (end - start) * 1e6

        queue.put({"status": "built", "building_time_us": building_elapsed_time_us})

        # solving time
        start = time.perf_counter()
        model.optimize()
        end = time.perf_counter()
        solving_elapsed_time_us = (end - start) * 1e6

        queue.put(
            {
                "status": "done",
                "solving_time_us": solving_elapsed_time_us,
                "building_time_us": building_elapsed_time_us,
                "total_time_us": building_elapsed_time_us + solving_elapsed_time_us,
            }
        )

    except Exception as e:
        queue.put({"status": "error", "message": str(e)})


def run_sat_instance(path, queue):
    try:
        solver = BinPackingSAT(path)
        result = solver.solve_optimally(solver_name="cadical153")

        queue.put(
            {
                "status": "done",
                "optimal_bins": (
                    result.optimal_bins if result.feasible else "INFEASIBLE"
                ),
                "solving_time_us": result.solve_time_us,
                "building_time_us": result.build_time_us,
                "total_time_us": result.total_time_us,
                "assignment": result.assignment,
                "sizes": solver.sizes,
                "capacity": solver.bin_capacity,
            }
        )

    except Exception as e:
        queue.put({"status": "error", "message": str(e)})


def run_with_timeout(target, path, timeout=TIME_LIMIT_SECONDS):
    queue = mp.Queue()
    process = mp.Process(target=target, args=(path, queue))
    process.start()

    start_time = time.perf_counter()
    last_message = None

    while process.is_alive():
        try:
            msg = queue.get(timeout=0.1)
            last_message = msg

            if msg.get("status") == "done":
                process.join()
                return msg

            if msg.get("status") == "error":
                process.join()
                return msg

        except Empty:
            pass

        if time.perf_counter() - start_time > timeout:
            process.terminate()
            process.join()
            return {"status": "timeout", "partial": last_message}

    while not queue.empty():
        last_message = queue.get()

    if last_message is not None:
        return last_message

    return {"status": "error", "message": "No result returned"}


if __name__ == "__main__":
    elapsed_times_4_all_problems = []

    print(Fore.RED + "Starting the experiment only for instance 3:\n")

    # -----------------------------------
    # m1 and m2 formulations with SCIP
    # Only P3
    # -----------------------------------
    p_path = "p3.json"
    formulations_path = ["m1_", "m2_"]

    for m_path in formulations_path:
        print(Fore.RED + f"Working on problem P3 with : {m_path}\n")

        path = "problems/" + m_path + p_path
        m = [["Solving Time", "Building Time", "Total Time"]]

        print(Fore.WHITE + f"Started problem : {m_path}{p_path}\n")

        for rep in range(REPETITIONS):
            print(Fore.CYAN + f"[{m_path}{p_path}] repetition {rep + 1}/{REPETITIONS}")

            result = run_with_timeout(run_mip_instance, path)

            if result["status"] == "timeout":
                print(
                    Fore.YELLOW
                    + f"Repetition {rep + 1}/{REPETITIONS} timed out (> {TIME_LIMIT_SECONDS}s)\n"
                )

                partial = result.get("partial")

                if partial and partial.get("status") == "built":
                    building_time = partial["building_time_us"]
                    m.append([TIMEOUT_LABEL, building_time, TIMEOUT_LABEL])
                else:
                    m.append([TIMEOUT_LABEL, TIMEOUT_LABEL, TIMEOUT_LABEL])

            elif result["status"] == "error":
                print(
                    Fore.YELLOW
                    + f"Error on repetition {rep + 1}/{REPETITIONS}: {result['message']}\n"
                )
                m.append(["ERROR", "ERROR", "ERROR"])

            elif result["status"] == "done":
                print(Fore.GREEN + f"Repetition {rep + 1}/{REPETITIONS} done.\n")
                m.append(
                    [
                        result["solving_time_us"],
                        result["building_time_us"],
                        result["total_time_us"],
                    ]
                )

        elapsed_times_4_all_problems.append(m)
        print(Fore.RED + f"Problem {m_path}{p_path} done.\n")

    # -----------------------------------
    # SAT formulation with PySAT
    # Only P3
    # -----------------------------------
    sat_p = "sat_p3.json"
    path = "problems/" + sat_p
    m = [["Optimal Bins", "Solving Time", "Building Time", "Total Time"]]

    print(Fore.RED + "Working on problem P3 with : SAT\n")
    print(Fore.WHITE + f"Started SAT problem : {sat_p}\n")

    for rep in range(REPETITIONS):
        print(Fore.CYAN + f"[{sat_p}] repetition {rep + 1}/{REPETITIONS}")

        result = run_with_timeout(run_sat_instance, path)

        if result["status"] == "timeout":
            print(
                Fore.YELLOW
                + f"SAT repetition {rep + 1}/{REPETITIONS} timed out (> {TIME_LIMIT_SECONDS}s)\n"
            )

            partial = result.get("partial")

            if partial and partial.get("status") == "built":
                building_time = partial["building_time_us"]
                m.append([TIMEOUT_LABEL, TIMEOUT_LABEL, building_time, TIMEOUT_LABEL])
            else:
                m.append([TIMEOUT_LABEL, TIMEOUT_LABEL, TIMEOUT_LABEL, TIMEOUT_LABEL])

        elif result["status"] == "error":
            print(
                Fore.YELLOW
                + f"Error on SAT repetition {rep + 1}/{REPETITIONS}: {result['message']}\n"
            )
            m.append(["ERROR", "ERROR", "ERROR", "ERROR"])

        elif result["status"] == "done":
            print(Fore.GREEN + f"SAT repetition {rep + 1}/{REPETITIONS} done.\n")

            m.append(
                [
                    result["optimal_bins"],
                    result["solving_time_us"],
                    result["building_time_us"],
                    result["total_time_us"],
                ]
            )

            if (
                result["optimal_bins"] != "INFEASIBLE"
                and result.get("assignment") is not None
            ):
                solution_filename = "Data/Data_sat_P3_solution.csv"

                write_sat_solution_to_csv(
                    assignment=result["assignment"],
                    sizes=result["sizes"],
                    capacity=result["capacity"],
                    filename=solution_filename,
                )

                print(Fore.GREEN + f"SAT solution saved in {solution_filename}\n")

    elapsed_times_4_all_problems.append(m)
    print(Fore.RED + f"SAT Problem {sat_p} done.\n")

    write_to_csv(elapsed_times_4_all_problems)
    print(Fore.RED + "Saved P3 data in csv files.\n")

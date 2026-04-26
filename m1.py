from src.modelBuilder import ModelBuilder
import time
import csv
import os
from colorama import Fore
import multiprocessing as mp
from queue import Empty

REPETITIONS = 50
TIME_LIMIT_SECONDS = 60
TIMEOUT_LABEL = f"{TIME_LIMIT_SECONDS}s+"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INSTANCES = [
    {
        "name": "m1_p1",
        "problem_path": os.path.join(BASE_DIR, "problems", "m1_p1.json"),
        "csv_path": os.path.join(BASE_DIR, "Data", "Data_m1_P1.csv"),
    },
    {
        "name": "m1_p2",
        "problem_path": os.path.join(BASE_DIR, "problems", "m1_p2.json"),
        "csv_path": os.path.join(BASE_DIR, "Data", "Data_m1_P2.csv"),
    },
    {
        "name": "m1_p3",
        "problem_path": os.path.join(BASE_DIR, "problems", "m1_p3.json"),
        "csv_path": os.path.join(BASE_DIR, "Data", "Data_m1_P3.csv"),
    },
]


def save_csv(csv_path, matrix):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    # "w" overwrites the existing CSV file
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(matrix)


def run_mip_instance(path, queue):
    try:
        # Building time
        start = time.perf_counter()
        model = ModelBuilder(path).build()
        model.hideOutput()
        end = time.perf_counter()

        building_time_us = (end - start) * 1e6

        queue.put({"status": "built", "building_time_us": building_time_us})

        # Solving time
        start = time.perf_counter()
        model.optimize()
        end = time.perf_counter()

        solving_time_us = (end - start) * 1e6

        queue.put(
            {
                "status": "done",
                "solving_time_us": solving_time_us,
                "building_time_us": building_time_us,
                "total_time_us": solving_time_us + building_time_us,
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

            if msg.get("status") in ["done", "error"]:
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
    print(Fore.RED + "Starting experiment only for m1_p1, m1_p2, m1_p3\n")

    for instance in INSTANCES:
        name = instance["name"]
        problem_path = instance["problem_path"]
        csv_path = instance["csv_path"]

        print(Fore.RED + f"Started instance: {name}\n")

        matrix = [["Solving Time", "Building Time", "Total Time"]]

        for rep in range(REPETITIONS):
            print(Fore.CYAN + f"[{name}] repetition {rep + 1}/{REPETITIONS}")

            result = run_with_timeout(run_mip_instance, problem_path)

            if result["status"] == "timeout":
                print(
                    Fore.YELLOW
                    + f"Repetition {rep + 1}/{REPETITIONS} timed out (> {TIME_LIMIT_SECONDS}s)\n"
                )

                partial = result.get("partial")

                if partial and partial.get("status") == "built":
                    building_time = partial["building_time_us"]
                    matrix.append([TIMEOUT_LABEL, building_time, TIMEOUT_LABEL])
                else:
                    matrix.append([TIMEOUT_LABEL, TIMEOUT_LABEL, TIMEOUT_LABEL])

            elif result["status"] == "error":
                print(
                    Fore.YELLOW
                    + f"Error on repetition {rep + 1}/{REPETITIONS}: {result['message']}\n"
                )

                matrix.append(["ERROR", "ERROR", "ERROR"])

            elif result["status"] == "done":
                print(Fore.GREEN + f"Repetition {rep + 1}/{REPETITIONS} done.\n")

                matrix.append(
                    [
                        result["solving_time_us"],
                        result["building_time_us"],
                        result["total_time_us"],
                    ]
                )

        save_csv(csv_path, matrix)

        print(Fore.GREEN + f"Saved and overwritten: {csv_path}\n")

    print(Fore.RED + "Finished all 3 instances.\n")

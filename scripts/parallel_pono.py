#!/usr/bin/env python3
from __future__ import annotations

import argparse
import enum
import os
import signal
import subprocess
import sys
import time


class ReturnCode(enum.Enum):
    """Return codes corresponding to enum values in pono/core/proverresult.h."""

    SEGFAULT = -signal.SIGSEGV
    SAT = 0
    UNSAT = 1
    ERROR = 2
    UNKNOWN = 255


SOLVED_RETURN_CODES = {ReturnCode.SAT.value, ReturnCode.UNSAT.value}


def main():
    parser = argparse.ArgumentParser(description="Run multiple engines in parallel")
    parser.add_argument("btor_file")
    parser.add_argument(
        "-k", "--bound", default=1000, type=int, help="The maximum bound to unroll to"
    )
    parser.add_argument(
        "-s", "--smt-solver", default="btor", help="Default SMT solver to use"
    )
    args = parser.parse_args()

    def get_command(arguments: list[str]) -> list[str]:
        command = ["pono", "-k", str(args.bound), *arguments]
        if "interp" in arguments or "ic3ia" in arguments:
            # Interpolation requires MathSat
            command.extend(["--smt-solver", "msat"])
        else:
            command.extend(["--smt-solver", args.smt_solver])
            if "--ceg-bv-arith" in command:
                # BV UF abstraction doesn't work with plain Boolector
                command.append("--logging-smt-solver")
        command.append(args.btor_file)
        return command

    pono_arguments = {
        "BMC": ["-e", "bmc"],
        "K-Induction": ["-e", "ind"],
        "Interpolant-based": ["-e", "interp"],
        "IC3IA": ["-e", "ic3ia", "--pseudo-init-prop"],
        "IC3IA-UF": ["-e", "ic3ia", "--pseudo-init-prop", "--ceg-bv-arith"],
        "IC3IA-NoUCG": ["-e", "ic3ia", "--pseudo-init-prop", "--no-ic3-unsatcore-gen"],
        "IC3IA-FTS": ["-e", "ic3ia", "--static-coi"],
        "IC3SA": ["-e", "ic3sa", "--static-coi"],
        "IC3SA-UF": ["-e", "ic3sa", "--static-coi", "--ceg-bv-arith"],
    }

    processes: dict[str, tuple[subprocess.Popen[str], float]] = {}

    def terminate_all():
        for process, _ in processes.values():
            if process.poll() is None:
                process.terminate()

    def handle_signal(signum, frame):
        # send signal recieved to subprocesses
        terminate_all()
        sys.exit(ReturnCode.UNKNOWN.value)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    for name, pono_args in pono_arguments.items():
        cmd = get_command(pono_args)
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=open(os.devnull, "w"), text=True
        )
        processes[name] = proc, time.time()

    while processes:
        for name, (process, start_time) in list(processes.items()):
            end_time = time.time()
            if process.poll() is not None:
                del processes[name]
                if process.returncode == ReturnCode.UNKNOWN.value:
                    continue
                try:
                    result = ReturnCode(process.returncode).name.lower()
                except ValueError:
                    result = f"error({process.returncode})"
                duration = end_time - start_time
                command = " ".join(get_command(pono_arguments[name]))
                print(result, f"{duration:.1f}", name, command, sep=",")
                if process.returncode in SOLVED_RETURN_CODES:
                    break
        else:
            time.sleep(0.05)
            continue
        terminate_all()
        break


if __name__ == "__main__":
    main()

"""In-container execution harness for CodeRazz sandbox.

Runs student solution.py against input.txt with strict output limits and execution metrics.
Outputs a structured JSON payload to stdout.
"""

import json
import os
import subprocess
import sys
import time

MAX_OUTPUT_BYTES = 65536  # 64 KB output limit


def run_harness():
    solution_path = "/app/solution.py"
    input_path = "/app/input.txt"

    if not os.path.exists(solution_path):
        result = {
            "exit_code": 1,
            "stdout": "",
            "stderr": "Error: solution.py not found in sandbox environment.",
            "runtime_ms": 0,
            "memory_kb": 0,
            "truncated": False,
            "error": "MISSING_SOLUTION_FILE",
        }
        print(json.dumps(result))
        sys.exit(0)

    # Read input data if present
    input_data = b""
    if os.path.exists(input_path):
        try:
            with open(input_path, "rb") as f:
                input_data = f.read()
        except Exception as e:
            input_data = str(e).encode()

    start_time = time.perf_counter()

    try:
        # Launch student code in isolated subprocess inside container
        proc = subprocess.Popen(
            [sys.executable, "-u", solution_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout_bytes, stderr_bytes = proc.communicate(input=input_data)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # Output truncation check
        truncated = False
        if len(stdout_bytes) > MAX_OUTPUT_BYTES:
            stdout_bytes = stdout_bytes[:MAX_OUTPUT_BYTES]
            truncated = True

        if len(stderr_bytes) > MAX_OUTPUT_BYTES:
            stderr_bytes = stderr_bytes[:MAX_OUTPUT_BYTES]
            truncated = True

        stdout_text = stdout_bytes.decode("utf-8", errors="replace")
        stderr_text = stderr_bytes.decode("utf-8", errors="replace")

        # Memory usage extraction via resource module if on Linux
        memory_kb = 0
        try:
            import resource

            usage = resource.getrusage(resource.RUSAGE_CHILDREN)
            memory_kb = usage.ru_maxrss
        except Exception:
            memory_kb = 0

        result = {
            "exit_code": proc.returncode,
            "stdout": stdout_text,
            "stderr": stderr_text,
            "runtime_ms": elapsed_ms,
            "memory_kb": memory_kb,
            "truncated": truncated,
            "error": None if proc.returncode == 0 else f"Process exited with code {proc.returncode}",
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        result = {
            "exit_code": 1,
            "stdout": "",
            "stderr": f"Harness execution failure: {str(exc)}",
            "runtime_ms": elapsed_ms,
            "memory_kb": 0,
            "truncated": False,
            "error": str(exc),
        }

    # Print structured JSON payload
    print(json.dumps(result))


if __name__ == "__main__":
    run_harness()


#!/usr/bin/env python
import argparse
import contextlib
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path
from pprint import pprint

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _parse_args():
    parser = argparse.ArgumentParser(description="Run local map conversion and validate artifacts.")
    parser.add_argument("--map-path", required=True, help="Path to input .map file.")
    parser.add_argument("--base-directory", default=r"L:\ce", help="Base CE directory.")
    parser.add_argument("--output-directory", default=r"L:\ce\output", help="Output directory root.")
    parser.add_argument("--log-file", default="test_local_e2e.log", help="Log file path.")
    parser.add_argument("--baseline-output-listing", default="tests/baselines/output_folder_contents.txt")
    parser.add_argument("--expected-min-images", type=int, default=300)
    parser.add_argument("--max-duration-ms", type=float, default=30000.0)
    return parser.parse_args()


def _run_conversion(args):
    from convert_map import map_to_glb

    map_path = Path(args.map_path).resolve()
    base_directory = Path(args.base_directory).resolve()
    output_directory = Path(args.output_directory).resolve()
    log_file = Path(args.log_file).resolve()

    if not map_path.is_file():
        raise FileNotFoundError(f"Input map does not exist: {map_path}")

    os.makedirs(base_directory, exist_ok=True)
    os.makedirs(output_directory, exist_ok=True)

    start = time.perf_counter()
    with log_file.open("w", encoding="utf-8") as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            print(f"Running local conversion for: {map_path}")
            result = map_to_glb(str(map_path), str(base_directory), str(output_directory))
            pprint(result)
            duration_ms = (time.perf_counter() - start) * 1000.0
            print(f"duration: {duration_ms:.3f}ms")
    return result, log_file


def main():
    args = _parse_args()

    try:
        result, log_file = _run_conversion(args)
    except Exception:
        log_file = Path(args.log_file).resolve()
        with log_file.open("w", encoding="utf-8") as log:
            traceback.print_exc(file=log)
        print(f"Local conversion failed. See {log_file}")
        return 1

    map_name = result["map_name"]
    output_map_dir = Path(args.output_directory).resolve() / map_name

    validate_script = PROJECT_ROOT / "tests" / "validation" / "validate_conversion_run.py"
    validate_cmd = [
        sys.executable,
        str(validate_script),
        "--output-map-dir",
        str(output_map_dir),
        "--map-name",
        map_name,
        "--log-file",
        str(log_file),
        "--expected-min-images",
        str(args.expected_min_images),
        "--max-duration-ms",
        str(args.max_duration_ms),
    ]
    baseline_path = Path(args.baseline_output_listing)
    if baseline_path.is_file():
        validate_cmd.extend(["--baseline-output-listing", str(baseline_path.resolve())])

    proc = subprocess.run(validate_cmd, check=False)
    if proc.returncode != 0:
        print(f"Validation failed. See {log_file}")
        return proc.returncode

    print("Local E2E run completed successfully")
    print(f"- map_name: {map_name}")
    print(f"- output_map_dir: {output_map_dir}")
    print(f"- log_file: {log_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

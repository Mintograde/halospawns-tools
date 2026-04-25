#!/usr/bin/env python
import argparse
import re
import sys
from pathlib import Path


def _parse_args():
    parser = argparse.ArgumentParser(description="Validate conversion output artifacts and logs.")
    parser.add_argument("--output-map-dir", required=True, help="Directory containing map output artifacts.")
    parser.add_argument("--map-name", required=True, help="Map name stem (for example: pat_chillout).")
    parser.add_argument("--log-file", help="Optional log file to validate for error patterns and milestones.")
    parser.add_argument("--baseline-output-listing", help="Optional ls -lR output listing for image count baseline.")
    parser.add_argument("--expected-min-images", type=int, default=1, help="Minimum number of PNG files expected.")
    parser.add_argument("--max-duration-ms", type=float, default=30000.0, help="Maximum allowed duration from logs.")
    parser.add_argument(
        "--image-count-tolerance",
        type=float,
        default=0.10,
        help="Allowed relative image-count delta vs baseline (for example 0.10 = +/-10%%).",
    )
    return parser.parse_args()


def _count_png_in_listing(path):
    png_pattern = re.compile(r"\.png$", re.IGNORECASE)
    count = 0
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        filename = line.rsplit(maxsplit=1)[-1] if line.strip() else ""
        if png_pattern.search(filename):
            count += 1
    return count


def _parse_duration_ms(log_text):
    report_line = next((line for line in log_text.splitlines() if "REPORT RequestId" in line), None)
    if report_line:
        durations = re.findall(r"Duration:\s*([0-9]+(?:\.[0-9]+)?)\s*ms", report_line)
        if len(durations) >= 2:
            return float(durations[1])
        if durations:
            return float(durations[0])

    rtdone_match = re.search(r"duration:\s*([0-9]+(?:\.[0-9]+)?)ms", log_text, flags=re.IGNORECASE)
    if rtdone_match:
        return float(rtdone_match.group(1))
    return None


def _validate_required_files(output_map_dir, map_name):
    required = [
        f"{map_name}.glb",
        f"{map_name}.blend",
        f"{map_name}.json",
        f"{map_name}.obj",
        f"{map_name}.mtl",
        f"{map_name}_Lightmap.obj",
        f"{map_name}_Lightmap.mtl",
    ]
    failures = []
    for filename in required:
        path = output_map_dir / filename
        if not path.is_file():
            failures.append(f"Missing required file: {path}")
            continue
        if path.stat().st_size <= 0:
            failures.append(f"Required file is empty: {path}")
    return failures


def _validate_log_text(log_text, max_duration_ms):
    failures = []
    error_pattern = re.compile(r"(traceback|an error occurred|exception|error:)", re.IGNORECASE)
    ignored_fragments = (
        "No stderr captured",
        "No supported native filedialog package installed",
    )

    for line in log_text.splitlines():
        if any(fragment in line for fragment in ignored_fragments):
            continue
        if error_pattern.search(line):
            failures.append(f"Error pattern detected in log: {line.strip()}")
            break

    for marker in ("Command executed successfully.", "Exported as", "Saved as"):
        if marker not in log_text:
            failures.append(f"Expected log marker missing: {marker}")

    duration_ms = _parse_duration_ms(log_text)
    if duration_ms is not None and duration_ms > max_duration_ms:
        failures.append(f"Duration {duration_ms:.2f} ms exceeds max {max_duration_ms:.2f} ms")

    moved_match = re.search(r"Moved\s+(\d+)\s+to", log_text)
    moved_count = int(moved_match.group(1)) if moved_match else None
    copied_match = re.search(r"Copied\s+(\d+)\s+images", log_text)
    copied_count = int(copied_match.group(1)) if copied_match else None
    return failures, duration_ms, moved_count, copied_count


def main():
    args = _parse_args()
    output_map_dir = Path(args.output_map_dir).resolve()
    failures = []

    if not output_map_dir.is_dir():
        print(f"FAIL: output directory does not exist: {output_map_dir}")
        return 1

    failures.extend(_validate_required_files(output_map_dir, args.map_name))

    png_files = list(output_map_dir.glob("*.png"))
    png_count = len(png_files)
    if png_count < args.expected_min_images:
        failures.append(
            f"PNG image count too low: found {png_count}, expected at least {args.expected_min_images}"
        )

    duration_ms = None
    moved_count = None
    copied_count = None
    if args.log_file:
        log_text = Path(args.log_file).read_text(encoding="utf-8", errors="replace")
        log_failures, duration_ms, moved_count, copied_count = _validate_log_text(log_text, args.max_duration_ms)
        failures.extend(log_failures)

    if moved_count is not None and png_count < max(1, int(moved_count * 0.90)):
        failures.append(f"PNG count {png_count} is unexpectedly low vs moved count {moved_count}")
    if copied_count is not None and png_count < max(1, int(copied_count * 0.90)):
        failures.append(f"PNG count {png_count} is unexpectedly low vs copied count {copied_count}")

    baseline_png_count = None
    if args.baseline_output_listing:
        baseline_png_count = _count_png_in_listing(args.baseline_output_listing)
        delta = abs(png_count - baseline_png_count)
        allowed_delta = max(1, int(baseline_png_count * args.image_count_tolerance))
        if delta > allowed_delta:
            failures.append(
                f"PNG count differs from baseline by {delta} (actual={png_count}, baseline={baseline_png_count}, "
                f"allowed={allowed_delta})"
            )

    if failures:
        print("VALIDATION FAILED")
        for item in failures:
            print(f"- {item}")
        return 1

    print("VALIDATION PASSED")
    print(f"- output_dir: {output_map_dir}")
    print(f"- map_name: {args.map_name}")
    print(f"- png_count: {png_count}")
    if baseline_png_count is not None:
        print(f"- baseline_png_count: {baseline_png_count}")
    if duration_ms is not None:
        print(f"- duration_ms: {duration_ms:.2f}")
    if moved_count is not None:
        print(f"- moved_count: {moved_count}")
    if copied_count is not None:
        print(f"- copied_count: {copied_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

import os
import shutil
import traceback

from conversion_runtime import resolve_directories, run_conversion


def resolve_io_mode(event):
    mode = (event.get("io_mode") or os.environ.get("IO_MODE", "s3")).strip().lower()
    if mode not in {"s3", "local"}:
        raise ValueError(f"Unsupported IO_MODE '{mode}'. Expected 's3' or 'local'.")
    return mode


def process_local_event(event):
    results = []

    try:
        base_directory, input_directory, output_directory = resolve_directories(event)
        local_input_map = event.get("local_input_map") or os.environ.get("LOCAL_INPUT_MAP")
        if not local_input_map:
            raise ValueError("Missing local map path. Provide event.local_input_map or LOCAL_INPUT_MAP.")

        local_input_map = os.path.abspath(local_input_map)
        if not os.path.isfile(local_input_map):
            raise FileNotFoundError(f"Local map file not found: {local_input_map}")

        stage_local_input = str(event.get("stage_local_input") or os.environ.get("STAGE_LOCAL_INPUT", "false")).lower() in {
            "1", "true", "yes"
        }
        map_file_path = local_input_map
        if stage_local_input:
            map_file_path = os.path.join(input_directory, os.path.basename(local_input_map))
            print(f"Staging local map file from {local_input_map} to {map_file_path}")
            shutil.copy2(local_input_map, map_file_path)

        print(f"Handling local conversion for {map_file_path}")
        result_path = run_conversion(map_file_path, base_directory, output_directory)
        if result_path:
            results.append({
                "input": map_file_path,
                "output": result_path,
                "status": "success"
            })
        else:
            results.append({
                "input": map_file_path,
                "status": "failure",
                "error": "map_to_glb failed; see logs"
            })

    except Exception as e:
        print(f"An error occurred processing local event: {e}")
        traceback.print_exc()
        results.append({
            "input": event.get("local_input_map") or os.environ.get("LOCAL_INPUT_MAP"),
            "error": str(e),
            "status": "failure"
        })

    return results

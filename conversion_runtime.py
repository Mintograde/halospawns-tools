import os
import sys
import traceback
from pprint import pprint

from convert_map import map_to_glb


def resolve_directories(event):
    base_directory = event.get("base_directory") or os.environ.get("CE_PATH", "/tmp/ce")
    output_directory = event.get("output_directory") or os.environ.get("OUTPUT_DIRECTORY", f"{base_directory}/output")
    input_directory = event.get("input_directory") or os.environ.get("INPUT_DIRECTORY", f"{base_directory}/input")

    os.makedirs(input_directory, exist_ok=True)
    os.makedirs(output_directory, exist_ok=True)

    return base_directory, input_directory, output_directory


def run_conversion(map_file_path, base_directory, output_directory):
    try:
        result_path = map_to_glb(map_file_path, base_directory, output_directory)
    except Exception:
        print("An error occurred:")
        traceback.print_exc(file=sys.stdout)
        return None

    pprint(result_path)
    return result_path

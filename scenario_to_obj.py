"""

    Input:  mapname.scenario
    Output: mapname.obj

    Use inspect.exe for control info

    Note: the data/ and tags/ directories must be present for Aether to start

"""
import glob
import os
import re
import shutil
import time
import subprocess
from pathlib import Path
from pprint import pprint

from obj_cleanup import aether_postprocess

CLEAN_PROJECT_FILES = True
CLEAN_DATA_FOLDER = True

aether_path = r"C:\Users\minto\Downloads\Aether\Aether.exe"
current_time = str(time.time()).replace(".","")
aeth_project_name = f'{current_time}.aeth'


def collect_images(image_filenames, destination_folder):
    """
    Copy all images into the specified folder, with new names (replacing spaces with dashes)
    """
    copied_files = {}
    for source_path in image_filenames:
        destination_filename = os.path.basename(source_path).replace(' ', '-')
        try:
            destination_path = shutil.copy2(source_path, os.path.join(destination_folder, destination_filename))
        except shutil.SameFileError:
            destination_path = source_path
        finally:
            copied_files[source_path] = destination_path
    return copied_files


def run_aether_and_get_paths(scenario_path, ce_path=None):
    """
    Runs the Aether tool and extracts specified file paths from its output.

    Args:
        scenario_path (str): The full path to the .scenario file to be processed.

    Returns:
        dict: A dictionary containing the extracted paths (e.g., 'folder', 'bsp').
              Returns None if the command fails or no data is found.
    """
    exe_path = os.environ.get(
        'AETHER_EXECUTABLE_PATH',
        r"L:\bens_stuff\projects\AetherCLI\bin\Debug\net8.0\AetherCLI.exe"
    )
    ce_path = str(ce_path or os.environ.get('CE_PATH', r"L:\ce"))

    command = [
        exe_path,
        '--hek-folder', ce_path.rstrip('/\\') + os.sep,
        '--bitmap-format', '3',
        '--bitmap-export', '1',
        '--overwrite-files', 'true',
        # '--saveconfig',
        str(scenario_path)
    ]

    print(f"Running command: {' '.join(command)}")

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            # shell=True,
            check=True,
            encoding='utf-8'
        )

        print("Command executed successfully.")
        print(f"Return Code: {result.returncode}")
        print("\n--- Full Tool STDOUT ---")
        print(result.stdout or "[No stdout captured]")
        print("------------------------\n")
        print("\n--- Full Tool STDERR ---")
        print(result.stderr or "[No stderr captured]")
        print("------------------------\n")

        extracted_data = {}
        pattern = re.compile(r"^@@(\w+)@@\s+(.*)$")
        for line in result.stdout.splitlines():
            if match := pattern.match(line.strip()):
                variable_name = match.group(1)
                file_path = Path(match.group(2))
                extracted_data[variable_name] = file_path
                if file_path.suffix == '.obj':
                    extracted_data[f'{variable_name}_mtl'] = file_path.with_suffix('.mtl')

        return extracted_data

    except FileNotFoundError:
        print(f"ERROR: The executable was not found at '{exe_path}'")
        print("Please ensure the path is correct.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"ERROR: The command failed with exit code {e.returncode}.")
        print("\n--- STDOUT ---")
        print(e.stdout)
        print("\n--- STDERR ---")
        print(e.stderr)
        return None


def scenario_to_obj(scenario_path, meta_filename=None, remove_lights=True, ce_path=None):
    ce_path = str(ce_path or os.environ.get('CE_PATH', r"L:\ce"))

    if CLEAN_DATA_FOLDER:
        try:
            shutil.rmtree(os.path.join(ce_path, 'data/levels'), ignore_errors=True)
        except OSError as e:
            print('Warning: could not clean data folder.')
            print(e)

    aether_output = run_aether_and_get_paths(scenario_path, ce_path=ce_path)

    if aether_output:
        print("Successfully extracted data:\n")

        for key, path in aether_output.items():
            print(f"  - {key:<16}: {path}")

        print("\n--- Accessing individual values ---")
        bsp_path = aether_output.get("bsp")
        if bsp_path:
            print(f"The BSP file is located at: {bsp_path}")

    else:
        print("\nScript finished with errors. No data was extracted.")

    aether_postprocess(aether_output['bsp'], remove_lights=remove_lights)
    aether_postprocess(aether_output['lightmap'], remove_lights=remove_lights, find_lightmaps=meta_filename is None, meta_filename=meta_filename)

    print('\n== Images generated ==')
    images = []
    for filename in glob.glob(os.path.join(ce_path, 'data') + '/**/*.png', recursive=True):
        images.append(filename)
        print(f' + {filename}')

    print('\n== Markers generated ==')
    markers = []
    print(f'finding markers in {os.path.join(ce_path)}/data/**/*.aemk')
    for filename in glob.glob(os.path.join(ce_path) + '/data/**/*.aemk', recursive=True):
        print(f' + {filename}')
        markers.append(filename)

    if CLEAN_PROJECT_FILES:
        print('\n== Removing Aether project files ==')
        for filename in glob.glob(os.path.join(ce_path, 'tags') + f'/**/{aeth_project_name}', recursive=True):
            print(f' - {filename}')
            os.remove(filename)

    # from pathlib import Path
    # folder = Path("/tmp/ce")
    # print('=== MTL FILES ===')
    # for f in folder.rglob("*.mtl"):
    #     if f.is_file():
    #         print(f)

    renamed_files = collect_images(images, aether_output['folder'])
    print(f'\nCopied {len(renamed_files)} images to {aether_output["folder"]}')
    return dict(
        project_name=aeth_project_name,
        map_name=aether_output['bsp'].stem,
        bsp_obj=aether_output['bsp'],
        bsp_mtl=aether_output['bsp_mtl'],
        lightmaps_obj=aether_output['lightmap'],
        lightmaps_mtl=aether_output['lightmap_mtl'],
        images=list(renamed_files.values()),
        markers=markers
    )


if __name__ == '__main__':

    pprint(scenario_to_obj(scenario_path=r"V:\test\tags\levels\test\prisoner\prisoner.scenario"))

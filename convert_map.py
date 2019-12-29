import os
import shutil
import subprocess
from pprint import pprint

from map_to_scenario import map_to_scenario
from scenario_to_obj import scenario_to_obj

BLENDER_PATH = r"L:\Program Files\Blender Foundation\Blender\blender.exe"


def map_to_glb(map_filename, base_directory, output_directory, keep_blend_files=False):

    scenario_filename, meta_filename = map_to_scenario(map_filename, base_directory)

    files = scenario_to_obj(scenario_path=scenario_filename)
    destination = os.path.join(output_directory, files['map_name'])
    destination_files = {}
    for file in [files['obj'], files['mtl'], *files['markers'], *files['images'], meta_filename]:
        os.makedirs(destination, exist_ok=True)
        destination_files[file] = shutil.move(file, os.path.join(destination, os.path.basename(file)))
    print(f'Moved {len(destination_files)} to {destination}')
    pprint(destination_files)

    # blender --background test.blend --python mytest.py -- example args 123
    args = [
        BLENDER_PATH,
        '--background',
        '--python',
        'blender.py',
        '--',
        destination_files[files['obj']],
    ]
    print(args)
    results = subprocess.run(args, capture_output=True, encoding='utf8')
    print('=== stdout ===')
    print(results.stdout)
    print('=== stderr ===')
    print(results.stderr)


if __name__ == '__main__':

    base_directory = r'L:\ce'
    output_directory = r'L:/ce/output/'
    map_filenames = [
        r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\chillout.map',
        r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\prisoner.map',
        r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\hangemhigh.map',
        r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\damnation.map',
        r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\beavercreek.map',
    ]
    for map_filename in map_filenames:
        map_to_glb(map_filename, base_directory, output_directory)

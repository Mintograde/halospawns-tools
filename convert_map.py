import os
import shutil

from map_to_scenario import map_to_scenario
from scenario_to_obj import scenario_to_obj


def map_to_glb(map_filename, base_directory, output_directory, keep_blend_files=False):

    scenario_filename = map_to_scenario(map_filename, base_directory)

    files = scenario_to_obj(scenario_path=scenario_filename)
    destination = os.path.join(output_directory, files['map_name'])
    for file in [files['obj'], files['mtl'], *files['markers'], *files['images']]:
        print(file)
        os.makedirs(destination, exist_ok=True)
        shutil.copy2(file, destination)

    # TODO: obj to glb in blender


if __name__ == '__main__':

    base_directory = r'L:\ce'
    output_directory = r'L:/ce/glb/'
    map_filenames = [
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\chillout.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\prisoner.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\hangemhigh.map',
        r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\damnation.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\beavercreek.map',
    ]
    for map_filename in map_filenames:
        map_to_glb(map_filename, base_directory, output_directory)

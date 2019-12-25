from map_to_scenario import map_to_scenario
from scenario_to_obj import scenario_to_obj


def map_to_glb(map_filename, base_directory):

    scenario_filename = map_to_scenario(map_filename, base_directory)

    obj_filename = scenario_to_obj(scenario_path=scenario_filename)

    # TODO: obj to glb in blender


if __name__ == '__main__':

    base_directory = r'L:\ce'
    map_filename = r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\chillout.map'
    map_to_glb(map_filename, base_directory)

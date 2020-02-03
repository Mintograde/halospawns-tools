"""

    https://discordapp.com/channels/331642419953139713/360988068901289985/601534076477767680
    L:\bens_stuff\projects\halospawns-tools\venv\Lib\site-packages\refinery\test_commands.txt


    python repl_run.py
    load-map "C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\chillout.map" --make-active 1
    set-vars --bitmap-extract-format "png" --data-dir "C:\test\data\" --recursive 1 --tags-dir "C:\test\tags\" --tagslist-path "C:\test\tags\tagslist.txt"
    extract-tags --tag-ids <scenario>

    available commands are in arg_parsers.py
    help info is in help_strs.py

"""
import json
import os
import shutil
from collections import defaultdict

from refinery import core


def map_to_scenario(filename, base_directory, delete_tags_directory=True):
    """
    Use Refinery from MEK to extract the .scenario tag from a .map file

    TODO:
        - netgame flags for portal from and portal to
        - scenery for trees and teleporters etc
        - netgame equipment for weapons/powerups/etc

    :param filename:
    :param base_directory:
    :param delete_tags_directory:
    :return:
    """

    if delete_tags_directory:
        shutil.rmtree(os.path.join(base_directory, 'tags'), ignore_errors=True)

    refinery_instance = core.RefineryCore()

    # load-map "C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\chillout.map" --make-active 1
    refinery_instance.enqueue('load_map', filepath=filename, make_active=1)

    # set-vars --bitmap-extract-format "png" --data-dir "C:\test\data\" --recursive 1 --tags-dir "C:\test\tags\" --tagslist-path "C:\test\tags\tagslist.txt"
    variables = dict(
        bitmap_extract_format='png',
        recursive=1,
        tags_dir=os.path.join(base_directory, 'tags'),
        tagslist_path=os.path.join(base_directory, 'tags/tagslist.txt'),
        # do_printout=1  # prints entire list of extracted tags
    )
    names = list(variables.keys())
    values = list(variables.values())
    refinery_instance.enqueue('set_vars', names=names, values=values)

    # extract-tags --tag-ids <scenario>
    refinery_instance.enqueue('extract_tags', tag_ids=['<scenario>'], overwrite=1)
    refinery_instance.process_queue()

    # find exported scenario file, and rename if needed
    # FIXME: find a better way of doing this
    scenario_path = ''
    with open(refinery_instance.tagslist_path, 'r') as f:
        for line in f.readlines():
            if line.strip().endswith('.scenario'):
                scenario_path = os.path.join(base_directory, 'tags/', line[line.find(':')+2:-1])
                break
    if not scenario_path:
        raise Exception('unable to find exported scenario filename in tagslist.txt')
    parent_directory = os.path.basename(os.path.dirname(scenario_path))
    scenario_filename = os.path.splitext(os.path.basename(scenario_path)[0])
    if parent_directory != scenario_filename:
        new_scenario_path = os.path.join(os.path.dirname(scenario_path), f'{parent_directory}.scenario')
        old_scenario_path = scenario_path
        scenario_path = shutil.move(scenario_path, new_scenario_path)
        print(f'Renamed "{old_scenario_path}" to "{new_scenario_path}"')

    # get extra metadata (spawns, scenery, teleporters, and equipment locations)
    meta = refinery_instance.active_map.scnr_meta
    spawns_array = meta.player_starting_locations.player_starting_locations_array
    spawns_list = []
    for i, spawn in enumerate(spawns_array):
        spawn_item = dict(
            x=spawn.position.x,
            y=spawn.position.y,
            z=spawn.position.z,
            facing=spawn.facing,
            team_index=spawn.team_index,
            bsp_index=spawn.bsp_index,
            type_0=spawn.type_0.data,
            type_1=spawn.type_1.data,
            type_2=spawn.type_2.data,
            type_3=spawn.type_3.data,
            type_0_name=spawn.type_0.enum_name,
            type_1_name=spawn.type_1.enum_name,
            type_2_name=spawn.type_2.enum_name,
            type_3_name=spawn.type_3.enum_name,
            spawn_index=i,
        )
        spawns_list.append(spawn_item)

    equip_array = meta.netgame_equipments.netgame_equipments_array
    equip_list = []
    for i, equip in enumerate(equip_array):
        equip_item = dict(
            x=equip.position.x,
            y=equip.position.y,
            z=equip.position.z,
            type_0=equip.type_0.data,
            type_1=equip.type_1.data,
            type_2=equip.type_2.data,
            type_3=equip.type_3.data,
            facing=equip.facing,
            team_index=equip.team_index,
            spawn_time=equip.spawn_time,
            filepath=equip.item_collection.filepath,
            levitate=equip.flags.get('levitate'),
            equip_index=i,
        )
        equip_list.append(equip_item)

    flags_array = meta.netgame_flags.netgame_flags_array
    flags_list = []
    teleporters = defaultdict(dict)
    for i, flag in enumerate(flags_array):
        flag_item = dict(
            x=flag.position.x,
            y=flag.position.y,
            z=flag.position.z,
            facing=flag.facing,
            team_index=flag.team_index,
            flag_type=flag.type.data,
            flag_type_name=flag.type.enum_name,
            flags_index=i,
        )
        if flag.type.enum_name in ('teleport_from', 'teleport_to'):
            teleporters[flag.team_index][flag.type.enum_name] = flag_item
        flags_list.append(flag_item)
    teleporters = list(teleporters.values())

    meta_json = json.dumps(
        dict(
            spawns=spawns_list,
            scenery=[],
            teleporters=teleporters,
            equipment=equip_list,
        )
    )
    meta_json_path = os.path.join(os.path.join(os.path.dirname(scenario_path), f'{parent_directory}.json'))
    with open(meta_json_path, 'w') as f:
        f.write(meta_json)

    return scenario_path, meta_json_path


if __name__ == '__main__':

    base_directory = r'C:\test'
    map_filename = r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\chillout.map'
    print(map_to_scenario(map_filename, base_directory))

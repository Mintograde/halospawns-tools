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
import re
import shutil
import sys
from io import StringIO

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

    # types are in ['STEPTREE'] -> ['NAME_MAP'] and [0, 1, 2...]

    scnr = refinery_instance.active_map.defs['scnr']
    tagdata = scnr.descriptor[scnr.descriptor['NAME_MAP']['tagdata']]

    active_map = refinery_instance.active_map
    desc = active_map.tag_index.desc
    index_ref = active_map.tag_index.scenario_tag_id
    # index_ref = active_map.tag_index[desc['NAME_MAP']['scenario_tag_id']]

    meta = refinery_instance.active_map.get_meta(
        index_ref & 0xFFff, True,
        # allow_corrupt=self.settings["allow_corrupt"].get(),
        # disable_safe_mode=disable_safe_mode,
        # disable_tag_cleaning=disable_tag_cleaning,
    )

    spawns_array = meta.player_starting_locations.player_starting_locations_array

    spawns_list = []
    for i, spawn in enumerate(spawns_array):
        spawn_dict = dict(
            x=spawn.position.x,
            y=spawn.position.y,
            z=spawn.position.z,
            facing=spawn.facing,
            team_index=spawn.team_index,
            bsp_index=spawn.bsp_index,
            type_0=spawn.type_0.data,
            type_0_name=spawn.type_0.enum_name,
            type_1=spawn.type_1.data,
            type_1_name=spawn.type_1.enum_name,
            type_2=spawn.type_2.data,
            type_2_name=spawn.type_2.enum_name,
            type_3=spawn.type_3.data,
            type_3_name=spawn.type_3.enum_name,
            spawn_index=i,
        )
        spawns_list.append(spawn_dict)

    # refinery_instance.enqueue('print_map_info')
    # old_stdout = sys.stdout
    # result = StringIO()
    # sys.stdout = result
    # refinery_instance.process_queue()
    # map_info = result.getvalue()
    # sys.stdout = old_stdout

    map_name = active_map.map_name
    scenario_path = os.path.join(base_directory, f'tags/levels/test/{map_name}/{map_name}.scenario')

    meta_json = json.dumps(
        dict(
            spawns=spawns_list,
            scenery=[],
            teleporters=[],
        )
    )
    meta_json_path = os.path.join(base_directory, f'tags/levels/test/{map_name}/{map_name}.json')
    with open(meta_json_path, 'w') as f:
        f.write(meta_json)

    return scenario_path, meta_json_path


if __name__ == '__main__':

    base_directory = r'C:\test'
    map_filename = r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\chillout.map'
    print(map_to_scenario(map_filename, base_directory))

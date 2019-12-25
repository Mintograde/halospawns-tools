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
import glob
import os
import shutil

from refinery import core


def map_to_scenario(filename):

    shutil.rmtree(os.path.join('C:/test/tags'), ignore_errors=True)

    refinery_instance = core.RefineryCore()

    # load-map "C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\chillout.map" --make-active 1
    refinery_instance.enqueue('load_map', filepath=filename, make_active=1)

    # set-vars --bitmap-extract-format "png" --data-dir "C:\test\data\" --recursive 1 --tags-dir "C:\test\tags\" --tagslist-path "C:\test\tags\tagslist.txt"
    variables = dict(
        bitmap_extract_format='png',
        # data_dir='C:\\test\\data\\',
        recursive=1,
        tags_dir='C:\\test\\tags\\',
        tagslist_path='C:\\test\\tags\\tagslist.txt',
        # do_printout=1
    )
    names = list(variables.keys())
    values = list(variables.values())
    refinery_instance.enqueue('set_vars', names=names, values=values)

    # extract-tags --tag-ids <scenario>
    refinery_instance.enqueue('extract_tags', tag_ids=['<scenario>'], overwrite=1)
    refinery_instance.process_queue()

    scenario_files = glob.glob(r'C:/test/tags/**/*.scenario', recursive=True)
    # for filename in scenario_files:
    #     print(os.path.join(filename))

    return scenario_files

    # refinery_instance.enqueue('print_map_info')
    # refinery_instance.process_queue()


if __name__ == '__main__':

    map_filename = r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\chillout.map'
    tag_directory = r'C:\test\tags'
    data_directory = r'C:\test\data'
    tagslist_path = r'C:\test\tags\tagslist.txt'
    map_to_scenario(map_filename)

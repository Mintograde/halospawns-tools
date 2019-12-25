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
import os
import re
import shutil
import sys
from io import StringIO

from refinery import core


def map_to_scenario(filename, base_directory, delete_tags_directory=True):

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

    refinery_instance.enqueue('print_map_info')
    old_stdout = sys.stdout
    result = StringIO()
    sys.stdout = result
    refinery_instance.process_queue()
    map_info = result.getvalue()
    sys.stdout = old_stdout

    map_name = ''
    m = re.search(' {4}name +== (?P<mapname>.+)\\n', map_info)
    if m:
        map_name = m.group('mapname')

    # scenario_files = glob.glob(f'C:/test/tags/levels/test/{map_name}/{map_name}.scenario', recursive=True)

    # TODO: get scenario path from mek directly
    return os.path.join(base_directory, f'tags/levels/test/{map_name}/{map_name}.scenario')


if __name__ == '__main__':

    base_directory = r'C:\test'
    map_filename = r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\chillout.map'
    print(map_to_scenario(map_filename, base_directory))

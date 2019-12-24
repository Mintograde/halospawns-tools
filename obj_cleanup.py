"""

    https://discordapp.com/channels/331642419953139713/360988068901289985/601534076477767680
    L:\bens_stuff\projects\halospawns-tools\venv\Lib\site-packages\refinery\test_commands.txt


    python repl_run.py
    load-map "C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\chillout.map" --make-active 1
    set-vars --bitmap-extract-format "png" --data-dir "C:\test\data\" --recursive 1 --tags-dir "C:\test\tags\" --tagslist-path "C:\test\tags\tagslist.txt"
    extract-tags --tag-ids <scenario>

    available commands are in arg_parsers.py
    help info is in help_strs.py

    player_starting_locations format
        first_element   +0xC (element length 52: 0x34)
            40 CE AF 10 3F 9D A1 77 40 18 7A 3A BF 49 0F DB 00 00 00 00 00 0D
            C0 D7 1E 30 41 27 8C D7 3A A3 06 1A BF 66 39 99 00 01 00 00 00 01
            big endian
            +0  float   x
            +4  float   y
            +8  float   z
            +12 float   facing (radians)
            +13 int8    bsp index? (-1 = NONE)
            +14 int8    team_index (0 or 1)
            +15 int8    type 3
            +16 int8    type 2
            +17 int8    type 1
            +18 int8    type 0

        types:
            0x0     none
            0x1     ctf
            0x2     slayer
            0x3     oddball
            0x4     king
            0x5     race
            0x6     terminator
            0x7     stub
            0x8     ignored1
            0x9     ignored2
            0xA     ignored3
            0xB     ignored4
            0xC     all games
            0xD     all games except ctf
            0xE     all games except ctf and race


"""
import os
import shutil


def convert(file_in, file_out):
    pass


def fix_line(line):
    return line.split(maxsplit=1)[1].\
        replace('"', '').\
        replace(' ', '-')


def aether_postprocess(obj_filename, relative_paths=True, copy_img=True):
    """
    Cleans up the given obj and associated mtl file by removing spaces and quotes
    from material names and images.

    # TODO: check if image files exist:
        - if old image exists and new does not, rename old to new
        - if new image exists, do nothing
        - if neither exists, show warning for missing images

    aether-postprocess
        in .mtl:
            for map_Kd, change
                "metal plate floor.png"
            to
                metal-plate-floor.png
            (remove quotes and spaces, and rename actual exported .png file)
    """

    directory = os.path.dirname(obj_filename)
    # print(obj_filename)
    # print(directory)

    # find mtl file
    mtl_filename = None
    with open(obj_filename) as f:

        out_lines = []
        for line in f:
            if line.startswith('mtllib'):
                # TODO: handle spaces / quotes
                line = line.replace('"', '')
                mtl_filename = line.split()[-1]
            elif line.startswith('usemtl'):
                line = f'usemtl {fix_line(line)}'
            out_lines.append(line)

    # modify obj file with new material names
    with open(obj_filename, 'w') as f:

        f.writelines(out_lines)

    if not mtl_filename:
        raise Exception('did not find .mtl filename in .obj')

    # modify mtl file contents and image filenames
    with open(os.path.join(directory, mtl_filename), 'r+') as f:

        out_lines = []
        for line in f:

            if line.startswith('map_Kd'):

                # get new filename
                old_filename = line.split(maxsplit=1)[1]
                old_filename = old_filename.replace('"', '')
                if relative_paths:
                    # TODO: support actual relative paths instead of same-dir, e.g. using os.path.relpath()
                    old_filename = os.path.basename(old_filename)
                new_filename = old_filename.replace(' ', '-')

                # rename or copy image with new name
                # old_path = os.path.join(directory, old_filename)
                # new_path = os.path.join(directory, new_filename)
                # if os.path.exists(old_path):
                #     if copy_img:
                #         print(f'renaming {old_path} to {new_path}')
                #         os.rename(old_path, new_path)
                #     else:
                #         print(f'copying {old_path} to {new_path}')
                #         shutil.copy2(old_path, new_path)

                line = f'map_Kd {new_filename}'

            elif line.startswith('newmtl'):

                line = f'newmtl {fix_line(line)}'

            out_lines.append(line)

    # write modified mtl file
    with open(os.path.join(directory, mtl_filename), 'w') as f:

        f.writelines(out_lines)


if __name__ == '__main__':

    # file_in = 'chillout.map'
    # file_out = 'chillout.glb'
    # convert(file_in, file_out)

    aether_postprocess(r"C:\tmp\prisoner-aether.obj")

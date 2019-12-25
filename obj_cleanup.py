"""




"""
import os
import re
import shutil


def convert(file_in, file_out):
    pass


def fix_line(line):
    return line.split(maxsplit=1)[1].\
        replace('"', '').\
        replace(' ', '-')


def aether_postprocess(obj_filename, relative_paths=True, copy_img=True, remove_lights=True):
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

    # TODO: better light/unwanted-object removal (*light removes too much)
    excluded_materials = re.compile('.*light$')

    # find mtl filename in obj
    mtl_filename = None
    with open(obj_filename) as f:

        out_lines = []
        in_excluded_segment = False
        for line in f:
            if line.startswith('mtllib'):
                # TODO: handle spaces / quotes
                line = line.replace('"', '')
                mtl_filename = line.split()[-1]
            elif line.startswith('usemtl'):
                line = f'usemtl {fix_line(line)}'
                in_excluded_segment = excluded_materials.match(line) is not None
            if not in_excluded_segment:
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

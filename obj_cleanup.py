"""




"""
import base64
import glob
import io
import itertools
import json
import os
import re
import shutil
import sys
from pathlib import Path
from pprint import pprint
import struct

IS_RUNNING_IN_LAMBDA = 'LAMBDA_TASK_ROOT' in os.environ

# if IS_RUNNING_IN_LAMBDA:
#     print('Skipping pillow import, running in AWS Lambda container')
# else:
#     try:
#         from PIL import Image
#     except ImportError as e:
#         # expected within aws python lambda containers
#         # print(f'WARNING: failed to load pillow: {e}')
#         Image = None
#         pass


from PIL import Image

def convert(file_in, file_out):
    pass


def fix_line(line):
    return line.split(maxsplit=1)[1].\
        replace('"', '').\
        replace(' ', '-')


# from https://stackoverflow.com/a/21555489
def get_image_info(data):
    if is_png(data):
        w, h = struct.unpack('>LL', data[16:24])
        width = int(w)
        height = int(h)
    else:
        raise Exception('not a png image')
    return width, height


def is_png(data):
    return data[:8] == b'\x89PNG\r\n\x1a\n' and (data[12:16] == b'IHDR')


# if we need to run in an environment without pillow support, this is an alternative way to get image sizes (png only)
def get_sizes(lightmap_files, from_base64=False):
    sizes = []
    for filename in lightmap_files:
        if from_base64:
            data = base64.b64decode(filename)
        else:
            with open(filename, 'rb') as f:
                data = f.read()
        if not is_png(data):
            print(f'WARNING: {filename} is not a PNG, skipping...')
            continue
        sizes.append(get_image_info(data))
    return sizes


def combine_lightmaps(lightmap_files, combined_filename, from_base64=False):

    images = []
    sizes = []
    total_width = 0
    total_height = 0

    for filename in lightmap_files:

        if from_base64:
            buf = io.BytesIO(base64.b64decode(filename))
            image = Image.open(buf)
        else:
            image = Image.open(filename)
        total_width += image.size[0]
        if total_height < image.size[1]:
            total_height = image.size[1]
        sizes.append(image.size)
        images.append(image)

    final_image = Image.new('RGB', (total_width, total_height), color='white')

    offset = 0
    for i, image in enumerate(images):
        final_image.paste(image, (offset, 0))
        offset += image.size[0]

    final_image.save(combined_filename)
    print(f'saved combined lightmap as {combined_filename}')
    return sizes


def aether_postprocess(obj_filename, relative_paths=True, copy_img=True, remove_lights=True, find_lightmaps=False, lightmap_files=None, meta_filename=None):
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

    # TODO: extract directly from lightmap mtl
    from_base64 = False
    if find_lightmaps:
        lightmap_files = sorted(list(Path(directory).glob(Path(obj_filename).stem.split('_')[0] + '_*.png')), key=lambda x: int(Path(x).stem.split('_')[-1]))
        print('found lightmap files:')
        for f in lightmap_files:
            print(f'  {f}')
    elif meta_filename:
        print(f'loading lightmap files from {meta_filename}')
        with open(meta_filename) as f:
            meta = json.load(f)
            if 'lightmap_base64' in meta:
                lightmap_files = meta['lightmap_base64']
                from_base64 = True
            else:
                lightmap_files = []
            # pprint(lightmap_files)

        with open(meta_filename, 'w') as f:
            if 'lightmap_base64' in meta:
                del meta['lightmap_base64']
            if 'lightmap_images' in meta:
                del meta['lightmap_images']
            json.dump(meta, f)

    if lightmap_files:
        # combined_filename = Path(directory).joinpath(Path(lightmap_files[0]).stem + '_lightmap.png')
        # new_material_name = Path(lightmap_files[0]).stem + '_lightmap'
        combined_filename = str(Path(obj_filename).parent.absolute() / 'lightmap.png')
        new_material_name = 'lightmap'
        # print('=== sys.modules ===')
        # pprint(sys.modules)
        # print('=== dir() ===')
        # pprint(dir())
        # print('=== end ===')
        if 'PIL' in sys.modules and 'PIL.Image' in sys.modules:
            print('pillow loaded, combining lightmaps and gathering sizes...')
            lightmap_sizes = combine_lightmaps(lightmap_files, combined_filename, from_base64=from_base64)
        else:
            print('pillow not loaded, gathering lightmap sizes...')
            lightmap_sizes = get_sizes(lightmap_files, from_base64=from_base64)
        widths = [size[0] for size in lightmap_sizes]
        width = sum(widths)
        height = max([size[1] for size in lightmap_sizes])
        pixel_offsets = list(itertools.accumulate(widths))
        pixel_offsets.pop()
        pixel_offsets.insert(0, 0)
        uv_offsets = [px / width for px in pixel_offsets]
    else:
        lightmap_sizes = []

    # return


    # find mtl filename in obj
    mtl_filename = None
    with open(obj_filename) as f:

        out_lines = []
        in_excluded_segment = False
        first_vt_line = -1
        fixed_vt_indices = {}  # starts at 1, so target line is first_vt_line + vt_index (-1?)
        current_material = ''
        current_material_index = 0
        vertex_pattern = re.compile('f(?: \d+/(\d+)/\d+ \d+/(\d+)/\d+ \d+/(\d+)/\d+)')
        uv_pattern = re.compile('vt (?P<u>.+) (?P<v>.+) .+')
        for line in f:
            if line.startswith('mtllib'):
                # TODO: handle spaces / quotes
                line = line.replace('"', '')
                mtl_filename = line.split()[-1]
            elif line.startswith('usemtl'):
                material_name = fix_line(line)
                line = f'usemtl {material_name}\n'
                in_excluded_segment = excluded_materials.match(line) is not None
                if lightmap_files:
                    line = line.replace(material_name, new_material_name)
                    current_material = material_name
                    current_material_index = int(material_name.split('_')[-1])
            elif line.startswith('vt '):
                if first_vt_line == -1:
                    first_vt_line = len(out_lines)
                    # print('first vt line is', first_vt_line)
            elif lightmap_files and line.startswith('f '):
                # f 4780/4780/4780 4778/4778/4778 4781/4781/4781
                m = vertex_pattern.match(line)
                # print(m.groups())
                for vertex_index in m.groups():
                    vertex_index = int(vertex_index)
                    if vertex_index not in fixed_vt_indices:
                        # vt 0.2060141 0.9537249 0
                        vt_line = out_lines[first_vt_line + vertex_index - 1]
                        uv_match = uv_pattern.match(vt_line)
                        u, v = float(uv_match.group('u')), float(uv_match.group('v'))
                        new_u = u * (widths[current_material_index] / width) + uv_offsets[current_material_index]
                        new_v = v * (lightmap_sizes[current_material_index][1] / height) + (1 - lightmap_sizes[current_material_index][1] / height)
                        out_lines[first_vt_line + vertex_index - 1] = f'vt {new_u} {new_v} 0\n'
                        fixed_vt_indices[vertex_index] = out_lines[first_vt_line + vertex_index - 1]
                        # print(f'line {first_vt_line + vertex_index} for vert_index {vertex_index}, part of {current_material.strip()} ({lightmap_sizes[current_material_index]}, {uv_offsets[current_material_index]}): {vt_line.strip()} -> {out_lines[first_vt_line + vertex_index - 1].strip()}')
            if not in_excluded_segment or not remove_lights:
                out_lines.append(line)

    # modify obj file with new material names
    with open(obj_filename, 'w') as f:
        print(f'Saving as {obj_filename}...')
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
                    if lightmap_files:
                        # old_filename = Path(lightmap_files[0]).stem + '_lightmap.png'
                        old_filename = 'lightmap.png'
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

                if lightmap_files:
                    line = f'newmtl {new_material_name}\n'
                else:
                    line = f'newmtl {fix_line(line)}'

            out_lines.append(line)

            if line.startswith('map_Kd') and lightmap_files:
                break

    # write modified mtl file
    with open(os.path.join(directory, mtl_filename), 'w') as f:
        print(f'Writing {len(out_lines)} lines to {os.path.join(directory, mtl_filename)}...')
        f.writelines(out_lines)

    return obj_filename, os.path.join(directory, mtl_filename)


if __name__ == '__main__':

    # file_in = 'chillout.map'
    # file_out = 'chillout.glb'
    # convert(file_in, file_out)

    # aether_postprocess(r"C:\tmp\prisoner-aether.obj")
    aether_postprocess(f"L:\ce\output\chillout\chillout_Lightmap.obj",
                       remove_lights=False,
                       lightmap_files=[
                           "L:\ce\output\chillout\chillout_0.png",
                           "L:\ce\output\chillout\chillout_1.png",
                           "L:\ce\output\chillout\chillout_2.png",
                           "L:\ce\output\chillout\chillout_3.png",
                           "L:\ce\output\chillout\chillout_4.png",
                           "L:\ce\output\chillout\chillout_5.png",
                           "L:\ce\output\chillout\chillout_6.png",
                           "L:\ce\output\chillout\chillout_7.png",
                           "L:\ce\output\chillout\chillout_8.png",
                       ])

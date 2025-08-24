r"""

    https://discordapp.com/channels/331642419953139713/360988068901289985/601534076477767680
    L:\bens_stuff\projects\halospawns-tools\venv\Lib\site-packages\refinery\test_commands.txt



    refinery==2.2.3
    python repl_run.py
    load-map "C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\chillout.map" --make-active 1
    set-vars --bitmap-extract-format "png" --data-dir "C:\test\data\" --recursive 1 --tags-dir "C:\test\tags\" --tagslist-path "C:\test\tags\tagslist.txt"
    extract-tags --tag-ids <scenario>

    available commands are in arg_parsers.py (venv\Lib\site-packages\refinery\repl\arg_parsers.py)
    help info is in help_strs.py (venv\Lib\site-packages\refinery\repl\help_strs.py)


    bsp data is at:
        refinery_instance.active_map.defs.sbsp.descriptor.1.12.STEPTREE.SUB_STRUCT
    See here for obj
        https://github.com/Sigmmma/mek/blob/master/tools_misc/wrl_to_obj.py#L100
    and here for sbsp parsing
        https://github.com/Sigmmma/mek/blob/master/tools_misc/Sbsp_Sotr_Replacer.py


"""
import base64
import glob
import json
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path
from pprint import pprint


# IS_RUNNING_IN_LAMBDA = 'LAMBDA_TASK_ROOT' in os.environ
#
# if IS_RUNNING_IN_LAMBDA:
#     print('Skipping mozzarilla import')
# else:
#     print('Loading Mozzarilla')
#     from mozzarilla.windows.tag_converters.sbsp_converter import sbsp_to_mod2


from mozzarilla.windows.tag_converters.sbsp_converter import sbsp_to_mod2
from reclaimer.model.model_decompilation import extract_model
from refinery import core
from reclaimer.hek.defs.sbsp import sbsp_def


def sbsp_to_gbxmodel(filepath):
    """
    Note: import the resulting .gbxmodel into blender with
        https://haloce3.com/downloads/applications/blender-gbxmodel-importer-v0-5-1/

    correctly named shaders are in
        gbxmodel.data.tagdata.shaders

    Issue: halo material properties (breakable, climbable, etc) aren't imported by blendkrieg

        The issue seems to be with loading the resulting gbxmodel into blender with blendkrieg.
        When blendkrieg loads the shaders, reclaimer strips the parameters off the name when it loads it into a JmsMaterial.
        See reclaimer.model.jms.JmsMaterial (material.py)

        Workaround for above: storing properties string in blender custom properties during blendkrieg import
            # blendkrieg model.py
            def import_halo1_model_shader(name="", properties=""):
                if bpy.data.materials.get(name, None) is None:
                    mat = bpy.data.materials.new(name=name)
                    mat['halo_properties'] = properties
            # blendkrieg halo1_model.py
            import_halo1_model_shader(mat.name, mat.properties)

    Issue: textures aren't included in blendkrieg import (and possibly not included in the gbxmodel export?)
        Need to store paths of exported pngs for later usage during Blender import
        Bitmaps from extract_data go through:
            core.py: RefineryCore.extract_tag()
            halo_map.py: HaloMap.extract_tag_data()
            bitmap_decompilation.py: extract_bitmaps()
                in extract_bitmaps(), added the following (around line 173):

                    with open(out_dir.joinpath('bitmap_paths.txt'), 'a') as f:
                        f.write(f'[{tag_path}][{filename_base}][{tex_info["filepath"]}]\n')

        https://github.com/Mintograde/reclaimer/commit/02b9105fed83486d7737a98aba8e0e57c8e684cf
        TODO: need to modify core.py extract_kw with pathname for above file

    Issue: some textures come from shaders. For instance on chillout, the `chillout alpha grate` texture in the gbxmodel
        is actually the shader `chillout alpha grate.shader_environment` which uses `covenant alpha grate.bitmap` as its
        base diffuse map -- see screenshots in https://docs.google.com/document/d/1kGtnTL9lf0z5QdsGWu8Qg-Ig5KXsMwm5o0d8avmNCU8/edit

        One thing to try:
            During import, if face uses a shader, just replace shader name with name diffuse base bitmap name

    :param filepath:
    :return:
    """

    gbxmodel = sbsp_to_mod2(sbsp_path=filepath)
    gbxmodel.serialize(temp=False, backup=False, int_test=False)
    shaders = gbxmodel.data.tagdata.shaders

    sbsp_tag = sbsp_def.build(filepath=filepath)

    print(gbxmodel.filepath)
    pass

    return gbxmodel


def sbsp_to_jms(filepath):

    gbxmodel = sbsp_to_mod2(sbsp_path=filepath)
    jms = extract_model(gbxmodel.data.tagdata, write_jms=True)
    return jms


def parse_sbsp(filepath):
    """
    Reclaimer usage:
        https://c20.reclaimers.net/tools/reclaimer/

        https://c20.reclaimers.net/h1/tags/scenario_structure_bsp/

    OBJ spec: http://www.martinreddy.net/gfx/3d/OBJ.spec
    MTL spec: http://www.fileformat.info/format/material/

    DCEL to OBJ: http://ranger.uta.edu/~weems/NOTES5319/LAB2/DCEL2obj.c

    https://haloce3.com/tutorials/lighting/Aether.htm

    OBJ example:
        mtllib wizard.mtl
        v 524.7261 993.7877 250         # v x y z w                             geometric vertices
        vt 6.214785 1.780233 0          # vt u v w                              texture vertices
        vn 0 -1 0                       # vn i j k                              vertex normals

        g wizard                        # g name                                group name
        usemtl steel                    # usemtl name                           material name
        f 3/3/3 2/2/2 1/1/1             # f v/vt/vn v/vt/vn v/vt/vn v/vt/vn     face
        usemtl panel-strip
        f 2/713/2 6/712/6 711/711/711

    Flags/materials:

        http://hce.halomaps.org/hek/index.html?start=references/general/materials_overview.html

            % double sided
            # transparent
            ! render only
            * large collidable
            $ fog plane
            ^ climbable
            - breakable
            & ai deafening
            @ collision only
            . exact portal

        https://discord.com/channels/228263208299790338/523620962390769695/770612993356333106
            "Add ^ to the end of the material you want climbable in your map"
            "If you make it just like a onesided card you'll want to add % to make it doublesided"
            "And potentially # if you want it transparent"
            "^%#"
        https://discord.com/channels/228263208299790338/577227356918513665/580319560817967124
            "yeah, @ is for non-rendered collision that acts just like the rest of the levels collision and * is for player clip(just tested)"
        https://discord.com/channels/228263208299790338/577227356918513665/580311606123298828



    :param filepath:
    :return:
    """

    sbsp_tag = sbsp_def.build(filepath=filepath)

    tag_data = sbsp_tag.data.tagdata
    bsp_surfaces = tag_data.collision_bsp.STEPTREE[0].surfaces.STEPTREE
    collision_materials = tag_data.collision_materials.collision_materials_array
    nonstandard_surfaces = []
    shader_properties = []
    for surface in bsp_surfaces:
        # if surface.flags.breakable or surface.breakable_surface or surface.flags.invisible or surface.flags.two_sided:
        if surface.flags.data != 0:
            print(surface)
            print(collision_materials[surface.material])
            nonstandard_surfaces.append(surface)


    gbxmodel = sbsp_to_mod2(sbsp_path=filepath)
    gbxmodel.serialize(temp=False, backup=False, int_test=False)
    shaders = gbxmodel.data.tagdata.shaders.shaders_array

    for shader in shaders:
        print(shader.shader.filepath)
        shader_properties.append(shader.shader.filepath)



    # collision_materials = tag_data.collision_materials
    # for material in collision_materials:
    #     print(material.)
    pass

    return shader_properties



def map_to_scenario(filename, base_directory, delete_tags_directory=True, delete_data_directory=True, extract_all=True):
    """
    Use Refinery from MEK to extract the .scenario tag from a .map file

    extract_data {  'queue_item_iid': 'data: map: chillout: bitm\\',
                    'tag_ids': [1176, 658, ..., 667],
                    'recursive': 1,
                    'overwrite': 1,
                    'do_printout': 1,
                    'autoload_resources': 1,
                    'decode_adpcm': 1,
                    'bitmap_extract_keep_alpha': 1,
                    'generate_comp_verts': 0,
                    'generate_uncomp_verts': 1,
                    'extract_mode': 'data',
                    'tagslist_path': 'L:\\bens_stuff\\projects\\halospawns-tools\\venv\\Lib\\site-packages\\refinery\\tags\\tagslist.txt',
                    'allow_corrupt': 0,
                    'skip_seen_tags_during_queue_processing': 1,
                    'disable_safe_mode': 0,
                    'disable_tag_cleaning': 0,
                    'bitmap_extract_format': 'png',
                    'globals_overwrite_mode': '0',
                    'out_dir': 'L:\\bens_stuff\\projects\\halospawns-tools\\venv\\Lib\\site-packages\\refinery\\data',
                    'engine': 'halo1ce',
                    'map_name': 'chillout'}

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
        tags_directory = os.path.join(base_directory, 'tags')
        print(f'Deleting {tags_directory}')
        shutil.rmtree(tags_directory, ignore_errors=True)
    if delete_data_directory:
        data_directory = os.path.join(base_directory, 'data')
        print(f'Deleting {data_directory}')
        shutil.rmtree(data_directory, ignore_errors=True)

    print('Loading Refinery')
    refinery_instance = core.RefineryCore()

    # load-map "C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\chillout.map" --make-active 1
    print(f'Loading map "{filename}"')
    refinery_instance.enqueue('load_map', filepath=filename, make_active=1)

    # set-vars --bitmap-extract-format "png" --data-dir "C:\test\data\" --recursive 1 --tags-dir "C:\test\tags\" --tagslist-path "C:\test\tags\tagslist.txt"
    variables = dict(
        bitmap_extract_format='png',
        recursive=1,
        tags_dir=os.path.join(base_directory, 'tags'),
        data_dir=os.path.join(base_directory, 'data'),
        tagslist_path=os.path.join(base_directory, 'tags/tagslist.txt'),
        # do_printout=1  # prints entire list of extracted tags
    )
    print('Setting Refinery variables:')
    pprint(variables)
    names = list(variables.keys())
    values = list(variables.values())
    refinery_instance.enqueue('set_vars', names=names, values=values)

    # extract-tags --tag-ids <scenario>
    # venv/Lib/site-packages/refinery/tag_index/tag_path_tokens.py
    refinery_instance.enqueue('extract_tags', tag_ids=['<scenario>'], overwrite=1)
    # refinery_instance.enqueue('extract_data', tag_ids=['<>'], overwrite=1)
    if extract_all:
        refinery_instance.enqueue('extract_data', tag_ids=['<all_tags>'], overwrite=1)
    # refinery_instance.enqueue('extract_tags', tag_ids=[0], overwrite=1)
    # refinery_instance.enqueue('extract_tags', tag_ids=['<scenario_structure_bsp>'], overwrite=1)
    print('Processing Refinery queue')
    refinery_instance.process_queue()
    print('Done. Postprocessing data')

    # from pathlib import Path
    # folder = Path("/tmp/ce")
    # for f in folder.rglob("*"):
    #     if f.is_file():
    #         print(f)

    active_map = refinery_instance.active_map

    # extract list of light emitting materials and normal/detail maps
    shader_metas = []
    shader_tags = []
    shader_attributes = {}
    for tag in active_map.tag_index.tag_index:
        if tag.class_1.enum_name == 'shader_transparent_chicago' and tag.path.startswith('levels\\'):
            tag_id = tag.id & 0xFFFF
            shader_meta = active_map.get_meta(tag_id)
            for bitmap in shader_meta.schi_attrs.maps.maps_array:
                if tag.path in shader_attributes:
                    print(f'WARNING: {tag.path} has multiple bitmaps')
                    print(f'    power: {shader_meta.shdr_attrs.radiosity_light_power} color: {(shader_meta.shdr_attrs.radiosity_light_color.r,shader_meta.shdr_attrs.radiosity_light_color.g,shader_meta.shdr_attrs.radiosity_light_color.b)}| {tag.path}')
                shader_attributes[tag.path] = dict(
                    shader_type=tag.class_1.enum_name,
                    short_name=tag.path.split('\\')[-1].replace(' ', '-'),
                    bitmap_path=bitmap.bitmap.filepath,
                    radiosity_power=shader_meta.shdr_attrs.radiosity_light_power,
                    radiosity_light_color=(shader_meta.shdr_attrs.radiosity_light_color.r,
                                           shader_meta.shdr_attrs.radiosity_light_color.g,
                                           shader_meta.shdr_attrs.radiosity_light_color.b),
                    alpha_tested=shader_meta.schi_attrs.chicago_shader.chicago_shader_flags.alpha_tested,
                    decal=shader_meta.schi_attrs.chicago_shader.chicago_shader_flags.decal,
                )
            shader_metas.append(shader_meta)
            shader_tags.append(tag)

        # venv/Lib/site-packages/reclaimer/hek/defs/senv.py
        elif tag.class_1.enum_name == 'shader_environment' and tag.path.startswith('levels\\'):
            tag_id = tag.id & 0xFFFF
            shader_meta = active_map.get_meta(tag_id)
            attrs = shader_meta.senv_attrs
            shader_attributes[tag.path] = dict(
                shader_type=tag.class_1.enum_name,
                short_name=tag.path.split('\\')[-1].replace(' ', '-'),
                diffuse_bitmap_path=attrs.diffuse.base_map.filepath,
                diffuse_primary_detail_map=attrs.diffuse.primary_detail_map.filepath,
                diffuse_secondary_detail_map=attrs.diffuse.secondary_detail_map.filepath,
                diffuse_micro_detail_map=attrs.diffuse.micro_detail_map.filepath,
                diffuse_material_color=(attrs.diffuse.material_color.r,
                                        attrs.diffuse.material_color.g,
                                        attrs.diffuse.material_color.b),
                bump_scale=attrs.bump_properties.map_scale,
                bump_bitmap_path=attrs.bump_properties.map.filepath,
                specular_brightness=attrs.specular.brightness,
                specular_perpendicular_color=(attrs.specular.perpendicular_tint_color.r,
                                              attrs.specular.perpendicular_tint_color.g,
                                              attrs.specular.perpendicular_tint_color.b),
                specular_parallel_color=(attrs.specular.parallel_tint_color.r,
                                         attrs.specular.parallel_tint_color.g,
                                         attrs.specular.parallel_tint_color.b),
                alpha_tested=attrs.environment_shader.flags.alpha_tested,
                bump_map_is_specular_mask=attrs.environment_shader.flags.bump_map_is_specular_mask,
                true_atmospheric_fog=attrs.environment_shader.flags.true_atmospheric_fog,
            )
            shader_tags.append(tag)
            shader_metas.append(shader_meta)

    # find exported scenario file, and rename if needed (scenario file gets loaded later by Aether for )
    # FIXME: find a better way of doing this
    scenario_path = None
    sbsp_path = None
    base_path = Path(base_directory)

    with open(refinery_instance.tagslist_path, 'r') as f:
        for line in f.readlines():
            if ':' in line:
                relative_path_str = line[line.find(':') + 2:-1].strip().replace('\\', '/')
                if relative_path_str.endswith('.scenario'):
                    scenario_path = base_path / 'tags' / relative_path_str
                elif relative_path_str.endswith('.scenario_structure_bsp'):
                    sbsp_path = base_path / 'tags' / relative_path_str

    if not scenario_path:
        raise Exception('unable to find exported scenario filename in tagslist.txt')

    parent_directory = scenario_path.parent.name
    scenario_filename_stem = scenario_path.stem

    if parent_directory != scenario_filename_stem:
        new_scenario_path = scenario_path.with_name(f'{parent_directory}.scenario')
        old_scenario_path = scenario_path

        print(f'Renaming "{old_scenario_path}" to "{new_scenario_path}"')
        scenario_path = Path(shutil.move(old_scenario_path, new_scenario_path))
        print(f'Renamed "{old_scenario_path}" to "{new_scenario_path}"')

    # FIXME: get bitmap names directly from tag list instead of globbing after export
    print(f"Finding lightmaps in {os.path.join(base_directory, 'data', f'**/{parent_directory}/{parent_directory}*.png')}")
    lightmap_images = list(glob.glob(os.path.join(base_directory, 'data', f'**/{parent_directory}/{parent_directory}*.png'), recursive=True))
    filter(re.compile(fr'{parent_directory}(__)?\d*\.png').match, lightmap_images)
    if len(lightmap_images) > 1:
        lightmap_images = sorted(lightmap_images, key=lambda x: int(Path(x).stem.split('__')[-1]))
    lightmap_base64 = []
    for image in lightmap_images:
        print(f'base64 encoding lightmap: {image}')
        with open(image, mode='rb') as f:
            img = f.read()
            lightmap_base64.append(base64.encodebytes(img).decode('utf-8'))

    shader_properties = []
    if sbsp_path:
        shader_properties = parse_sbsp(sbsp_path)
#
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
            shader_attributes=shader_attributes,
            shader_properties=shader_properties,
            lightmap_images=lightmap_images,
            lightmap_base64=lightmap_base64,
        )
    )
    meta_json_path = os.path.join(os.path.join(os.path.dirname(scenario_path), f'{parent_directory}.json'))
    with open(meta_json_path, 'w') as f:
        f.write(meta_json)

    return scenario_path, meta_json_path


if __name__ == '__main__':
    # parse_sbsp(r"L:\ce\tags\levels\test\chillout\chillout.scenario_structure_bsp")
    # parse_sbsp(r"L:\ce\_tags\levels\test\prisoner\prisoner.scenario_structure_bsp")
    # parse_sbsp(r"L:\ce\_tags\levels\test\damnation\damnation.scenario_structure_bsp")
    # sbsp_to_gbxmodel(r"L:\ce\_tags\levels\test\prisoner\prisoner.scenario_structure_bsp")
    # sbsp_to_gbxmodel(r"L:\ce\_tags\levels\test\damnation\damnation.scenario_structure_bsp")
    # sbsp_to_gbxmodel(r"C:\test\_tags\levels\test\chillout\chillout.scenario_structure_bsp")

    base_directory = r'C:\test'
    map_filename = r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\prisoner.map'
    # map_filename = r'C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE\maps\calamity.map'
    print(map_to_scenario(map_filename, base_directory, extract_all=False))

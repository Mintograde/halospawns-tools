"""

    TODO: auto selection -- for now, select imported obj before running

    https://blender.stackexchange.com/a/8405
    https://blender.stackexchange.com/a/1366
    blender --background test.blend --python mytest.py -- example args 123

    # TODO: normal maps: https://styly.cc/tips/blender-mapping/
            either in blender or threejs https://stackoverflow.com/questions/29800214/normal-map-in-obj-file

"""
import json
import os

import bpy
import sys

def main():
    # --- Argument Parsing ---
    # Get command-line arguments after "--"
    try:
        argv = sys.argv[sys.argv.index("--") + 1:]
        if len(argv) < 3:
            raise ValueError("Not enough arguments provided.")
        obj_path = argv[0]
        lightmaps_path = argv[1]
        meta_path = argv[2]
    except (ValueError, IndexError) as e:
        print(f"Error: Could not parse command-line arguments. Please provide obj_path, lightmaps_path, and meta_path.")
        print(f"Details: {e}")
        # B4-FIX: Ensure Blender exits with an error code if args are wrong.
        sys.exit(1)

    obj_directory = os.path.dirname(obj_path)
    obj_filename = os.path.splitext(os.path.basename(obj_path))[0]

    # --- Scene Cleanup ---
    print("Clearing default scene...")
    # B4-FIX: A more robust way to delete all objects.
    if bpy.data.objects:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()

    # --- Import and Process Objects ---
    imported_objects = []
    # B4-FIX: The loop was fine, but we'll use a more descriptive name.
    for path in [obj_path, lightmaps_path]:
        print(f'Importing "{path}"')

        # B4-FIX: The OBJ import operator was moved.
        # OLD: bpy.ops.import_scene.obj(filepath=path)
        bpy.ops.wm.obj_import(filepath=path)

        # After import, the new object is selected and active.
        if not bpy.context.selected_objects:
            print(f"Error: Import of '{path}' failed to create any objects.")
            sys.exit(1)

        obj_object = bpy.context.active_object
        print(f'Imported obj as "{obj_object.name}"')

        # obj_object.select_set(True)
        bpy.context.view_layer.objects.active = obj_object

        obj_object.scale = (0.01, 0.01, 0.01)
        obj_object.rotation_euler[0] = 0
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

        # bpy.ops.object.editmode_toggle()
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.remove_doubles()

        imported_objects.append(obj_object)

        obj_object.select_set(False)

    # bpy.context.object.select_all(action='DESELECT')
    # bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    # select target object
    imported_objects[0].select_set(True)
    # bpy.context.view_layer.objects.active = bpy.data.objects[0]

    # add and select a new uvmap
    new_uv_map = bpy.data.meshes[0].uv_layers.new(name='UVMap.001')
    bpy.data.meshes[0].uv_layers[0].active = False
    new_uv_map.active = True

    # select source object
    imported_objects[1].select_set(True)
    bpy.context.view_layer.objects.active = imported_objects[1]
    bpy.data.meshes[1].uv_layers[0].active = True

    # transfer uvmaps from source object to target object's second uvmap
    print('Copying UVs')
    print(f'Selected objects: {bpy.context.selected_objects}')
    print(f'Active object: {bpy.context.active_object}')
    print(f'Mesh 0 {bpy.data.meshes[0].name} UVs: {bpy.data.meshes[0].uv_layers}')
    print(f'Mesh 1 {bpy.data.meshes[1].name} UVs: {bpy.data.meshes[1].uv_layers}')
    # https://docs.blender.org/api/current/bpy.ops.object.html#bpy.ops.object.data_transfer
    print(bpy.ops.object.data_transfer(data_type='UV'))

    imported_objects[0].name = 'map'
    imported_objects[0].data.name = 'map'
    imported_objects[1].name = 'lightmap'
    imported_objects[1].data.name = 'lightmap'


    # set material properties and attach bump maps
    # https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/principled.html#examples

    with open(meta_path) as f:
        content = f.read()
        scene = bpy.context.scene
        scene['halospawns_metadata'] = content

        # empty = bpy.data.objects.new("HaloExtras", None)
        # bpy.context.collection.objects.link(empty)
        # empty["halospawns_metadata"] = content

        # imported_objects[0].data['metadata'] = content
        shaders = json.loads(content)['shader_attributes']
        for shader in shaders.values():
            if shader['short_name'] in bpy.data.objects['map'].material_slots:
                material = bpy.data.objects['map'].material_slots[shader['short_name']].material
                # print(f"{shader['short_name']}: {shader['shader_type']}")
                material['shader_type'] = shader['shader_type']
                material['alpha_tested'] = shader['alpha_tested']



    # bpy.context.space_data.context = 'DATA'
    # bpy.ops.mesh.uv_texture_add()
    # bpy.context.object.data.active_index = 1


    # TODO: for each light-emitting shader, merge adjacent faces and add an area light at merged face's position
    #       https://blender.stackexchange.com/a/7152
    #       https://c20.reclaimers.net/h1/tools/aether/#lighting
    #       lightmap baking: https://blenderartists.org/t/blender-cycles-lightmap-baking/1169571/9

    glb_path = os.path.join(obj_directory, f'{obj_filename}.glb')
    bpy.ops.export_scene.gltf(
        filepath=glb_path,
        export_format='GLB',
        export_apply=True,
        check_existing=False,
        export_extras=True,
        # axis_up='-Y'
    )
    print(f'Exported as {glb_path}')

    blend_path = os.path.join(obj_directory, f'{obj_filename}.blend')
    bpy.ops.wm.save_as_mainfile(
        filepath=blend_path,
        check_existing=False,
    )
    print(f'Saved as {blend_path}')

    # bpy.ops.select_similar(type='MATERIAL', threshold=0.01)
    # bpy.ops.mesh.delete(type='FACE')

    # light_materials = [
    #     'chillout-yellow-light',
    #     'chillout-blue-light',
    #     'chillout-blue-black-light',
    #     'chillout-yellow-black-light',
    #     'chillout-greenlight'
    # ]
    # bpy.context.object.active_material_index = bpy.data.materials[light_materials]

    # bpy.ops.object.material_slot_select()
    # bpy.ops.mesh.delete(type='FACE')


if __name__ == '__main__':
    main()
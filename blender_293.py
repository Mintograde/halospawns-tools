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

# bpy.data.objects['hangemhigh.005'].select_set(state=True)

argv = sys.argv[sys.argv.index("--") + 1:]
obj_path = argv[0]
obj_directory = os.path.dirname(obj_path)
obj_filename = os.path.splitext(obj_path)[0]
lightmaps_path = argv[1]
lightmaps_directory = os.path.dirname(lightmaps_path)
lightmaps_filename = os.path.splitext(lightmaps_path)[0]
meta_path = argv[2]

# delete starter objects
bpy.data.meshes.remove(bpy.data.objects['Cube'].data)
for o in bpy.context.scene.objects:
    o.select_set(True)
bpy.ops.object.delete()

objects = []

for obj in [obj_path, lightmaps_path]:
    print(f'Importing "{obj}"')
    bpy.ops.import_scene.obj(filepath=obj)
    obj_object = bpy.context.selected_objects[0]
    print(f'Imported obj as "{obj_object.name}"')

    # obj_object.select_set(True)
    bpy.context.view_layer.objects.active = obj_object
    bpy.context.object.scale[0] = 0.01
    bpy.context.object.scale[1] = 0.01
    bpy.context.object.scale[2] = 0.01
    bpy.context.object.rotation_euler[0] = 0
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # bpy.ops.object.editmode_toggle()
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    bpy.ops.mesh.remove_doubles()

    objects.append(obj_object)

    obj_object.select_set(False)

# bpy.context.object.select_all(action='DESELECT')
# bpy.ops.object.select_all(action='DESELECT')
bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

# select target object
objects[0].select_set(True)
# bpy.context.view_layer.objects.active = bpy.data.objects[0]

# add and select a new uvmap
new_uv_map = bpy.data.meshes[0].uv_layers.new(name='UVMap.001')
bpy.data.meshes[0].uv_layers[0].active = False
new_uv_map.active = True

# select source object
objects[1].select_set(True)
bpy.context.view_layer.objects.active = objects[1]
bpy.data.meshes[1].uv_layers[0].active = True

# transfer uvmaps from source object to target object's second uvmap
print('Copying UVs')
print(f'Selected objects: {bpy.context.selected_objects}')
print(f'Active object: {bpy.context.active_object}')
print(f'Mesh 0 {bpy.data.meshes[0].name} UVs: {bpy.data.meshes[0].uv_layers}')
print(f'Mesh 1 {bpy.data.meshes[1].name} UVs: {bpy.data.meshes[1].uv_layers}')
# https://docs.blender.org/api/current/bpy.ops.object.html#bpy.ops.object.data_transfer
print(bpy.ops.object.data_transfer(data_type='UV'))

objects[0].name = 'map'
objects[0].data.name = 'map'
objects[1].name = 'lightmap'
objects[1].data.name = 'lightmap'


# set material properties and attach bump maps
# https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/principled.html#examples

with open(meta_path) as f:
    shaders = json.load(f)['shader_attributes']
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

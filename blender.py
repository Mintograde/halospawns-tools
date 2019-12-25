"""

    TODO: auto selection -- for now, select imported obj before running

    https://blender.stackexchange.com/a/8405
    https://blender.stackexchange.com/a/1366
    blender --background test.blend --python mytest.py -- example args 123

"""
import os

import bpy
import sys

# bpy.data.objects['hangemhigh.005'].select_set(state=True)

argv = sys.argv[sys.argv.index("--") + 1:]
obj_path = argv[0]
obj_directory = os.path.dirname(obj_path)
obj_filename = os.path.splitext(obj_path)[0]

# remove default objects if they exist
try:
    bpy.data.objects['Camera'].select_set(True)
    bpy.ops.object.delete()
    bpy.data.objects['Light'].select_set(True)
    bpy.ops.object.delete()
    bpy.data.objects['Cube'].select_set(True)
    bpy.ops.object.delete()
except:
    pass

print(f'Importing "{obj_path}"')
imported_obj = bpy.ops.import_scene.obj(filepath=obj_path)
obj_object = bpy.context.selected_objects[0]
print(f'Imported obj as "{obj_object.name}"')

obj_object.select_set(True)
bpy.context.view_layer.objects.active = obj_object
bpy.context.object.scale[0] = 0.01
bpy.context.object.scale[1] = 0.01
bpy.context.object.scale[2] = 0.01
bpy.context.object.rotation_euler[0] = 0
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.editmode_toggle()
bpy.ops.mesh.remove_doubles()

glb_path = os.path.join(obj_directory, f'{obj_filename}.glb')
bpy.ops.export_scene.gltf(
    filepath=glb_path,
    export_format='GLB',
    export_apply=True,
    check_existing=False,
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

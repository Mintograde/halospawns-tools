import bpy

# TODO: auto selection -- for now, select imported obj before running
# bpy.data.objects['hangemhigh.005'].select_set(state=True)

bpy.context.object.scale[0] = 0.01
bpy.context.object.scale[1] = 0.01
bpy.context.object.scale[2] = 0.01
bpy.context.object.rotation_euler[0] = 0
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.editmode_toggle()
bpy.ops.mesh.remove_doubles()

# bpy.ops.select_similar(type='MATERIAL', threshold=0.01)
# bpy.ops.mesh.delete(type='FACE')

light_materials = [
    'chillout-yellow-light',
    'chillout-blue-light',
    'chillout-blue-black-light',
    'chillout-yellow-black-light',
    'chillout-greenlight'
]
# bpy.context.object.active_material_index = bpy.data.materials[light_materials]

# bpy.ops.object.material_slot_select()
# bpy.ops.mesh.delete(type='FACE')

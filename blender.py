import bpy

# TODO: auto selection -- for now, select imported obj before running
# bpy.data.objects['hangemhigh.005'].select_set(state=True)

bpy.context.object.scale[0] = 0.01
bpy.context.object.scale[1] = 0.01
bpy.context.object.scale[2] = 0.01
bpy.context.object.rotation_euler[0] = 0
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

import bpy
import os
import sys
import math
import mathutils

# Usage: blender -b -P blender_render.py -- <obj_path> <output_dir> <texture_path>

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def setup_lighting():
    # World
    world = bpy.context.scene.world
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs[0].default_value = (0.05, 0.05, 0.05, 1) # Dark ambient

    # Key Light (Warm, Front-Right)
    bpy.ops.object.light_add(type='AREA', location=(2, 2, 4))
    key = bpy.context.object
    key.data.energy = 500
    key.data.color = (1.0, 0.9, 0.8)
    key.data.size = 2
    # Point at center
    track_to(key, (0,0,0))

    # Fill Light (Cool, Left)
    bpy.ops.object.light_add(type='AREA', location=(-3, 1, 2))
    fill = bpy.context.object
    fill.data.energy = 300
    fill.data.color = (0.8, 0.9, 1.0)
    fill.data.size = 3
    track_to(fill, (0,0,0))

    # Rim Light (Bright, Back)
    bpy.ops.object.light_add(type='SPOT', location=(0, 4, 3)) # Back is +Y in Blender if looking from -Y? No, Front is usually -Y.
    # Let's say Camera is at (0, -3, 1). So Back is +Y.
    rim = bpy.context.object
    rim.location = (0, 3, 3) 
    rim.data.energy = 1000
    rim.data.color = (1, 1, 1)
    rim.data.spot_size = math.radians(60)
    track_to(rim, (0,0,0))
    
    # Point highlight
    bpy.ops.object.light_add(type='POINT', location=(1, -2, 2))
    pt = bpy.context.object
    pt.data.energy = 100

def track_to(obj, target_loc):
    # Damped Track to center
    constraint = obj.constraints.new(type='TRACK_TO')
    constraint.target = bpy.data.objects.new("Target", None)
    constraint.target.location = target_loc
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'

def import_obj_and_fix(obj_path, texture_path=None):
    # Try Import
    try:
        # Blender 4.0+
        bpy.ops.wm.obj_import(filepath=obj_path)
    except AttributeError:
        # Legacy
        bpy.ops.import_scene.obj(filepath=obj_path)
    
    imported_obs = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    
    # Create a container empty to rotate
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
    container = bpy.context.object
    container.name = "Container"
    
    # Process Meshes
    min_pt = [float('inf')]*3
    max_pt = [float('-inf')]*3
    
    # Calculate bounds first
    for obj in imported_obs:
        for v in obj.bound_box:
            # v is local, need world
            v_world = obj.matrix_world @ mathutils.Vector(v)
            for i in range(3):
                min_pt[i] = min(min_pt[i], v_world[i])
                max_pt[i] = max(max_pt[i], v_world[i])
    
    # Centering Vector
    center = (mathutils.Vector(min_pt) + mathutils.Vector(max_pt)) / 2
    
    # Parent and fix materials
    for obj in imported_obs:
        # Fix Material if texture provided and missing
        if texture_path and os.path.exists(texture_path):
            # Check if has material
            if not obj.data.materials:
                mat = bpy.data.materials.new(name="ForcedMat")
                obj.data.materials.append(mat)
            
            mat = obj.data.materials[0]
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            bsdf = nodes.get('Principled BSDF')
            
            # Check if image linked
            has_img = False
            if bsdf.inputs['Base Color'].is_linked:
                has_img = True
            
            if not has_img:
                tex_img = nodes.new('ShaderNodeTexImage')
                try:
                    tex_img.image = bpy.data.images.load(texture_path)
                    mat.node_tree.links.new(bsdf.inputs['Base Color'], tex_img.outputs['Color'])
                except:
                    pass
        
        # Shade Smooth
        # bpy.ops.object.shade_smooth() # Too aggressive? Auto Smooth is better.
        obj.data.use_auto_smooth = True
        obj.data.auto_smooth_angle = math.radians(30)
        
        # Center the geometry relative to container
        # Parent to container, but keep transform?
        # Better: Move object so center matches 0,0,0
        obj.location -= center
        obj.parent = container
        
    return container, (mathutils.Vector(max_pt) - mathutils.Vector(min_pt)).length

def setup_camera(scale_extent):
    bpy.ops.object.camera_add(location=(0, -1.8 * scale_extent, 0.8 * scale_extent))
    cam = bpy.context.object
    bpy.context.scene.camera = cam
    
    # Look at center
    constraint = cam.constraints.new(type='TRACK_TO')
    target = bpy.data.objects.get("Container") # Look at container
    constraint.target = target
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'
    
    # Zoom/Focal Length
    cam.data.lens = 50

def animate_rotation(obj, frames=30):
    obj.rotation_mode = 'XYZ'
    
    # Translate DOWN as requested (-0.15 relative to scale?)
    # If scale is normalized to ~1.0, -0.15 is good.
    # Our normalized scaling usually makes it unit size.
    # But here we imported raw. 
    # Let's adjust Z (up/down in Blender is Z) 
    # Wait, camera is side view? 
    # Usually Z is up. Front view is looking along Y.
    # So moving "Down" on screen means moving object -Z.
    
    # Start Frame
    obj.rotation_euler = (0, 0, 0)
    obj.keyframe_insert(data_path="rotation_euler", frame=1)
    
    # End Frame
    obj.rotation_euler = (0, 0, 2 * math.pi)
    obj.keyframe_insert(data_path="rotation_euler", frame=frames + 1)
    
    # Linear Interpolation
    for fcurve in obj.animation_data.action.fcurves:
        for kp in fcurve.keyframe_points:
            kp.interpolation = 'LINEAR'

def main():
    argv = sys.argv
    if "--" not in argv: return
    args = argv[argv.index("--") + 1:]
    
    obj_path = args[0]
    out_dir = args[1]
    tex_path = args[2] if len(args) > 2 else None
    
    reset_scene()
    
    # Import
    import mathutils
    container, extent = import_obj_and_fix(obj_path, tex_path)
    
    # Normalize Scale? 
    # User wanted "Zoom In". Easier to normalize object to unit size first.
    scale_factor = 1.0 / extent if extent > 0 else 1.0
    container.scale = (scale_factor, scale_factor, scale_factor)
    
    # Translate Down (Visual -Z)
    container.location.z -= 0.15
    
    setup_lighting()
    setup_camera(1.3) # 1.3 extent factor
    
    animate_rotation(container, frames=30)
    
    # Render Settings
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE' # or 'CYCLES'
    scene.render.film_transparent = True
    scene.render.resolution_x = 400
    scene.render.resolution_y = 400
    scene.render.resolution_percentage = 100
    
    scene.frame_start = 1
    scene.frame_end = 30
    
    # Output
    basename = os.path.basename(obj_path).replace(".obj", "")
    scene.render.filepath = os.path.join(out_dir, basename + "_")
    
    # Render Animation
    # bpy.ops.render.render(animation=True) 
    # We want to use CLI render usually, but calling here works too
    bpy.ops.render.render(animation=True)

if __name__ == "__main__":
    main()

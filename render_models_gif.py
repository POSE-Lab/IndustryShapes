import trimesh
import pyrender
import numpy as np
import os
from PIL import Image

# Force EGL or OSMesa
os.environ["PYOPENGL_PLATFORM"] = "egl"

def render_obj_gif(obj_path, save_path, frames=30):
    try:
        print(f"Loading {obj_path}...")
        
        fname = os.path.basename(obj_path)
        is_obj_5 = "000005" in fname
        needs_texture_fix = "000005" in fname or "000004" in fname
        
        # Load texture if needed
        texture_img = None
        tex_path = os.path.splitext(obj_path)[0] + ".png"
        if needs_texture_fix and os.path.exists(tex_path):
            try:
                texture_img = Image.open(tex_path).convert("RGBA")
            except:
                pass

        # Load mesh/scene 
        # process=False to avoid corrupting UVs, we will fix normals manually
        scene_or_mesh = trimesh.load(obj_path, force='mesh', process=False) 
        
        geometries = []
        if isinstance(scene_or_mesh, trimesh.Scene):
            geometries = list(scene_or_mesh.geometry.values())
        else:
            geometries = [scene_or_mesh]

        # Calculate Scene Extents
        all_vertices = []
        for geom in geometries:
            all_vertices.append(geom.vertices)
        
        centroid = np.zeros(3)
        scale = 1.0
        
        if all_vertices:
            all_vertices = np.vstack(all_vertices)
            min_pt = np.min(all_vertices, axis=0)
            max_pt = np.max(all_vertices, axis=0)
            centroid = (min_pt + max_pt) / 2.0
            extents = max_pt - min_pt
            max_extent = np.max(extents)
            scale = 1.0 / max_extent if max_extent > 0 else 1.0

        # Prepare Pyrender Scene
        scene = pyrender.Scene(bg_color=[0,0,0,0], ambient_light=[0.3, 0.3, 0.3])
        
        object_nodes = []

        # Process each geometry
        for geom in geometries:
            # Center and Scale (Global)
            geom.vertices -= centroid
            geom.apply_scale(scale)
            
            if is_obj_5:
                # Manual fixes instead of process=True
                trimesh.repair.fix_normals(geom)
                trimesh.repair.fix_winding(geom)
                
            # Force Texture Visual for Obj 5/4
            # We recreate the visual to ensure it binds the texture and UVs correctly
            if texture_img and hasattr(geom.visual, 'uv'):
                # geom.visual.uv contains UV encodings.
                # Create a new PBR material with the texture
                # Or just SimpleMaterial
                material = trimesh.visual.material.SimpleMaterial(image=texture_img)
                
                # We need to ensure we stick to TextureVisuals
                # If current visual is ColorVisuals, we need to promote it or use existing UVs
                # geom.visual = trimesh.visual.TextureVisuals(uv=geom.visual.uv, image=texture_img)
                # But simple assignment of material often works if visual is already TextureVisuals
                # Let's force it if it has UVs
                geom.visual.material = material

            # Create Pyrender Mesh
            try:
                mesh_pr = pyrender.Mesh.from_trimesh(geom, smooth=False)
                # Force double sided
                for prim in mesh_pr.primitives:
                    if prim.material: 
                        prim.material.doubleSided = True
                        if is_obj_5:
                            # Ensure metallic/roughness defaults usually handled by pyrender
                            # We can try to force it if accessible, but pyrender wraps it.
                            pass
            except:
                continue
                
            node = scene.add(mesh_pr)
            object_nodes.append(node)

        # Camera Setup (Zoomed In)
        camera = pyrender.PerspectiveCamera(yfov=np.pi / 3.0, aspectRatio=1.0)
        base_camera_pose = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 1.15], 
            [0.0, 0.0, 0.0, 1.0],
        ])
        scene.add(camera, pose=base_camera_pose)
        
        # Lighting
        key_pose = base_camera_pose.copy()
        rot_key = trimesh.transformations.rotation_matrix(np.deg2rad(45), [0, 1, 0])
        scene.add(pyrender.DirectionalLight(color=[1.0, 0.9, 0.8], intensity=5.0), pose=key_pose @ rot_key)
        
        fill_pose = base_camera_pose.copy()
        rot_fill = trimesh.transformations.rotation_matrix(np.deg2rad(-45), [0, 1, 0])
        scene.add(pyrender.DirectionalLight(color=[0.8, 0.9, 1.0], intensity=3.0), pose=fill_pose @ rot_fill)

        rim_pose = base_camera_pose.copy()
        rot_rim = trimesh.transformations.rotation_matrix(np.deg2rad(180), [0, 1, 0]) @ \
                  trimesh.transformations.rotation_matrix(np.deg2rad(-45), [1, 0, 0])
        scene.add(pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=6.0), pose=rim_pose @ rot_rim)
        
        scene.add(pyrender.PointLight(color=[1.0, 1.0, 1.0], intensity=10.0), pose=base_camera_pose)

        # Render
        r = pyrender.OffscreenRenderer(300, 300)
        images = []
        
        for i in range(frames):
            angle = 2 * np.pi * i / frames
            
            # Transforms
            rot_matrix = trimesh.transformations.rotation_matrix(angle, [0, 1, 0])
            tilt_matrix = trimesh.transformations.rotation_matrix(np.deg2rad(25), [1, 0, 0])
            
            # Shift Down! Y translation -0.15
            trans_matrix = np.eye(4)
            trans_matrix[1, 3] = -0.15 
            
            final_pose = trans_matrix @ tilt_matrix @ rot_matrix
            
            for node in object_nodes:
                scene.set_pose(node, pose=final_pose)
            
            color, _ = r.render(scene, flags=pyrender.RenderFlags.RGBA)
            img = Image.fromarray(color)
            images.append(img)
            
        images[0].save(save_path, save_all=True, append_images=images[1:], optimize=False, duration=100, loop=0, transparency=0, disposal=2)
        print(f"Saved {save_path}")
        r.delete()
        
    except Exception as e:
        print(f"Failed to render {obj_path}: {e}")
        import traceback
        traceback.print_exc()

def main():
    model_dir = "/home/lele/Downloads/IndustryShapes_textured_cad_models (1)/IndustryShapes_textured_cad_models"
    out_dir = "assets"
    
    if not os.path.exists(out_dir): os.makedirs(out_dir)
    
    for i in range(1, 6):
        fname = f"obj_{i:06d}.obj"
        path = os.path.join(model_dir, fname)
        if os.path.exists(path):
            render_obj_gif(path, os.path.join(out_dir, f"obj_{i:06d}.gif"))

if __name__ == "__main__":
    main()

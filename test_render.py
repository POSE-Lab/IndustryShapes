import trimesh
import pyrender
import numpy as np
import os
from PIL import Image

# Disable GUI
os.environ["PYOPENGL_PLATFORM"] = "egl" 

def render_test():
    # Create a simple sphere
    mesh = trimesh.creation.icosphere(radius=0.1)
    mesh_pr = pyrender.Mesh.from_trimesh(mesh)
    
    scene = pyrender.Scene()
    scene.add(mesh_pr)
    
    camera = pyrender.PerspectiveCamera(yfov=np.pi / 3.0, aspectRatio=1.0)
    s = np.sqrt(2)/2
    camera_pose = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.5],
        [0.0, 0.0, 0.0, 1.0],
    ])
    scene.add(camera, pose=camera_pose)
    
    light = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=2.0)
    scene.add(light, pose=camera_pose)
    
    try:
        r = pyrender.OffscreenRenderer(100, 100)
        color, depth = r.render(scene)
        img = Image.fromarray(color)
        img.save("test_render.png")
        print("Render successful")
    except Exception as e:
        print(f"Render failed: {e}")

if __name__ == "__main__":
    render_test()

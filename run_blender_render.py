import os
import subprocess
import glob
from PIL import Image

models_dir = "/home/lele/Downloads/IndustryShapes_textured_cad_models (1)/IndustryShapes_textured_cad_models"
out_dir = "/media/UbuntuStorage/papers/ICRA_IndustryShapes/gitio/assets/renders"
final_assets_dir = "/media/UbuntuStorage/papers/ICRA_IndustryShapes/gitio/assets"

if not os.path.exists(out_dir): os.makedirs(out_dir)

def make_gif(basename):
    # Find frames
    pattern = os.path.join(out_dir, f"{basename}_*.png")
    frames = sorted(glob.glob(pattern))
    if not frames:
        print(f"No frames found for {basename}")
        return

    images = [Image.open(f) for f in frames]
    save_path = os.path.join(final_assets_dir, f"{basename}.gif")
    
    images[0].save(save_path, save_all=True, append_images=images[1:], optimize=False, duration=100, loop=0, transparency=0, disposal=2)
    print(f"Created GIF: {save_path}")
    
    # Cleanup
    for f in frames:
        os.remove(f)

for i in range(1, 6):
    fname = f"obj_{i:06d}.obj"
    obj_path = os.path.join(models_dir, fname)
    tex_path = os.path.join(models_dir, f"obj_{i:06d}.png") # Fallback texture path
    
    basename = f"obj_{i:06d}"
    
    if os.path.exists(obj_path):
        print(f"Rendering {fname} with Blender...")
        
        # Call Blender
        # blinker -b -P script.py -- ARGS
        cmd = [
            "blender", "-b", "-P", "blender_script.py", "--",
            obj_path,
            out_dir,
            tex_path
        ]
        
        subprocess.run(cmd, check=False) # check=False to continue even if one fails (e.g. obj 5 weirdness)
        
        # Convert to GIF
        make_gif(basename)

print("All Blender renders finished.")

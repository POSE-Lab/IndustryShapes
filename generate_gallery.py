import json
import numpy as np
import os
import random
import shutil
from PIL import Image, ImageDraw, ImageFont

# --- Copied Core Logic from process_assets.py ---

def parse_obj_corners(obj_path):
    vertices = []
    try:
        with open(obj_path, 'r') as f:
            for line in f:
                if line.startswith('v '):
                    parts = line.split()
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
        if not vertices:
            return None
        vertices = np.array(vertices)
        min_pt = np.min(vertices, axis=0)
        max_pt = np.max(vertices, axis=0)
        return min_pt, max_pt
    except Exception as e:
        print(f"Error reading {obj_path}: {e}")
        return None

def get_box_corners_from_bounds(min_pt, max_pt):
    corners = np.array([
        [min_pt[0], min_pt[1], min_pt[2]],
        [max_pt[0], min_pt[1], min_pt[2]],
        [max_pt[0], max_pt[1], min_pt[2]],
        [min_pt[0], max_pt[1], min_pt[2]],
        [min_pt[0], min_pt[1], max_pt[2]],
        [max_pt[0], min_pt[1], max_pt[2]],
        [max_pt[0], max_pt[1], max_pt[2]],
        [min_pt[0], max_pt[1], max_pt[2]]
    ])
    return corners

def project_points(points_3d, R, t, K):
    points_c = (R @ points_3d.T) + t 
    us = []
    vs = []
    
    for i in range(points_c.shape[1]):
        x, y, z = points_c[:, i]
        if z <= 0: return None 
        u = (x * K[0, 0] / z) + K[0, 2]
        v = (y * K[1, 1] / z) + K[1, 2]
        us.append(u)
        vs.append(v)
        
    return list(zip(us, vs))

def draw_3d_box(draw, R, t, K, min_pt, max_pt, color=(0, 255, 0), scale=1.0):
    corners_3d = get_box_corners_from_bounds(min_pt, max_pt)
    corners_2d = project_points(corners_3d, R, t, K)
    if corners_2d is None: return

    corners_2d = [(x*scale, y*scale) for x, y in corners_2d]

    edges = [
        (0,1), (1,2), (2,3), (3,0), 
        (4,5), (5,6), (6,7), (7,4), 
        (0,4), (1,5), (2,6), (3,7)  
    ]
    
    width = max(2, int(3 * scale))
    
    for s, e in edges:
        draw.line([corners_2d[s], corners_2d[e]], fill=color, width=width)

def draw_axis(draw, R, t, K, length=60, scale=1.0):
    axis_points = np.array([
        [0, 0, 0],
        [length, 0, 0],  # X
        [0, length, 0],  # Y
        [0, 0, length]   # Z
    ])
    
    pts_2d = project_points(axis_points, R, t, K)
    if pts_2d is None: return
    
    pts_2d = [(x*scale, y*scale) for x, y in pts_2d]
    origin = pts_2d[0]
    
    width = max(3, int(6 * scale)) # Thicker axis
    
    draw.line([origin, pts_2d[1]], fill=(255, 0, 0), width=width) # X Red
    draw.line([origin, pts_2d[2]], fill=(0, 255, 0), width=width) # Y Green
    draw.line([origin, pts_2d[3]], fill=(0, 0, 255), width=width) # Z Blue

def load_objects_bounds(model_dir):
    bounds = {}
    print("Loading object models...")
    for i in range(1, 10): 
        fname = f"obj_{i:06d}.obj"
        path = os.path.join(model_dir, fname)
        if os.path.exists(path):
            res = parse_obj_corners(path)
            if res:
                bounds[i] = res
    return bounds

MODEL_DIR = "/home/lele/Downloads/IndustryShapes_textured_cad_models (1)/IndustryShapes_textured_cad_models"
OBJECT_BOUNDS = {}

def render_scene_image(scene_path, filename, scale_factor=1.0):
    """
    Renders a specific image from a scene with annotations.
    """
    global OBJECT_BOUNDS
    if not OBJECT_BOUNDS:
        OBJECT_BOUNDS = load_objects_bounds(MODEL_DIR)

    rgb_p = os.path.join(scene_path, 'rgb', filename)
    gt_p = os.path.join(scene_path, 'scene_gt.json')
    cam_p = os.path.join(scene_path, 'scene_camera.json')
    
    if not os.path.exists(rgb_p):
        print(f"Image not found: {rgb_p}")
        return None

    img = Image.open(rgb_p).convert("RGB")
    w, h = img.size
    
    # Render at higher res for quality then downscale? Or just render directly.
    # User wrapper upscales. Let's upscale slightly for smoother lines.
    render_scale = scale_factor * 2
    target_w, target_h = int(w * render_scale), int(h * render_scale)
    img_large = img.resize((target_w, target_h), resample=Image.BICUBIC)
    draw = ImageDraw.Draw(img_large)
    
    frame_key = str(int(os.path.splitext(filename)[0]))

    if os.path.exists(gt_p):
        with open(gt_p, 'r') as f: gt_data = json.load(f)
        with open(cam_p, 'r') as f: cam_data = json.load(f)
        
        # Format key to match json
        # Try both integer string and zero-padded? Usually standard is integer string "1"
        key = str(int(frame_key))
        
        if key in gt_data:
            cam_info = cam_data[key]
            # Handle list vs flattened
            K_raw = cam_info['cam_K']
            K = np.array(K_raw).reshape(3, 3)
            
            objects = gt_data[key]
            
            for obj in objects:
                obj_id = int(obj['obj_id'])
                R = np.array(obj['cam_R_m2c']).reshape(3, 3)
                t = np.array(obj['cam_t_m2c']).reshape(3, 1)
                
                if obj_id in OBJECT_BOUNDS:
                    min_pt, max_pt = OBJECT_BOUNDS[obj_id]
                    # Draw Green Box
                    draw_3d_box(draw, R, t, K, min_pt, max_pt, color=(0, 255, 0), scale=render_scale)
                    # Draw Axis
                    draw_axis(draw, R, t, K, length=70, scale=render_scale)
    
    img_final = img_large.resize((int(w*scale_factor), int(h*scale_factor)), resample=Image.LANCZOS)
    return img_final, img # Return annotated and original

# --- New Generation Logic ---

def get_image_list(scene_path):
    rgb_dir = os.path.join(scene_path, 'rgb')
    if not os.path.exists(rgb_dir): return []
    return sorted([f for f in os.listdir(rgb_dir) if f.endswith('.png')])

# --- Depth Processing ---
def get_depth_image(scene_path, filename, scale_factor=0.5):
    depth_path = os.path.join(scene_path, 'depth', filename)
    if not os.path.exists(depth_path): return None
    
    d_img = Image.open(depth_path)
    d_arr = np.array(d_img).astype(float)
    
    d_min = np.min(d_arr)
    d_max = np.max(d_arr)
    if d_max > d_min:
        d_norm = (d_arr - d_min) / (d_max - d_min)
    else:
        d_norm = np.zeros_like(d_arr)
        
    # Lava colormap: Black -> Red -> Yellow -> White
    h, w = d_norm.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    
    # 0.0 - 0.33: Black (0,0,0) -> Red (255,0,0)
    mask1 = d_norm < 0.33
    t1 = d_norm[mask1] / 0.33
    rgb[mask1, 0] = (t1 * 255).astype(np.uint8)
    
    # 0.33 - 0.66: Red (255,0,0) -> Yellow (255,255,0)
    mask2 = (d_norm >= 0.33) & (d_norm < 0.66)
    t2 = (d_norm[mask2] - 0.33) / 0.33
    rgb[mask2, 0] = 255
    rgb[mask2, 1] = (t2 * 255).astype(np.uint8)
    
    # 0.66 - 1.0: Yellow (255,255,0) -> White (255,255,255)
    mask3 = d_norm >= 0.66
    t3 = (d_norm[mask3] - 0.66) / 0.34
    rgb[mask3, 0] = 255
    rgb[mask3, 1] = 255
    rgb[mask3, 2] = (t3 * 255).astype(np.uint8)
    
    img = Image.fromarray(rgb, mode='RGB')
    
    # Resize matches annotation scale
    # To match render_scene_image (which uses scale_factor on original), we must know original first.
    # Depth usually same size as RGB.
    orig_w, orig_h = img.size
    target_w, target_h = int(orig_w * scale_factor), int(orig_h * scale_factor)
    return img.resize((target_w, target_h), Image.LANCZOS)


# --- GIF Generation Logic (Re-integrated & Enhanced) ---
def generate_gif(scene_path, save_path, frame_step=5, max_frames=60, start_frame=0):
    rgb_dir = os.path.join(scene_path, 'rgb')
    if not os.path.exists(rgb_dir): return
    
    files = sorted([f for f in os.listdir(rgb_dir) if f.endswith('.png')])
    
    # Apply start frame skipping
    # Synchronized Generation Logic
    # To Ensure sync loops, we must stick to exact frame count.
    
    available_files = []
    if start_frame < len(files):
        available_files = files[start_frame:]
    else:
        return 
        
    target_frames = 80
    if len(available_files) < target_frames:
        # Not enough frames? Just take what we have (and it will be shorter).
        # But to sync, maybe duplicate last? No that looks stuck.
        # User said "full around the object so include more frames".
        # Assume we have enough.
        selected_files = available_files
    else:
        # Dynamic step to fit exactly target_frames
        # We want to cover as much as possible?
        # User said "full around the object".
        # If we just take first 80, we cover small arc.
        # We should compute step.
        step = len(available_files) // target_frames
        if step < 1: step = 1
        selected_files = available_files[::step][:target_frames]
        
    total_frames = len(selected_files) # Should be 80 if enough data
    
    transition_start = int(total_frames * 0.4) # 32 if 80
    transition_dur = int(total_frames * 0.1)   # 8 if 80
    
    frames = []
    
    for idx, f_name in enumerate(selected_files):
        # ... logic same ...
        
        # Render Annotated RGB
        rgb_img, _ = render_scene_image(scene_path, f_name, scale_factor=0.5)
        if not rgb_img: continue
        rgb_img.thumbnail((400, 400))
        
        # Render Depth
        depth_img = get_depth_image(scene_path, f_name, scale_factor=0.5)
        if not depth_img: continue
        depth_img.thumbnail((400, 400))
        
        # Ensure sizes match
        if rgb_img.size != depth_img.size:
            depth_img = depth_img.resize(rgb_img.size)
            
        final_img = None
        
        # Using idx against transition window relative to this specific GIF length (which we try to keep constant)
        if idx < transition_start:
            final_img = rgb_img
        elif idx > (transition_start + transition_dur):
            final_img = depth_img
        else:
            # Blend
            alpha = (idx - transition_start) / transition_dur 
            final_img = Image.blend(rgb_img, depth_img, alpha)
            
        frames.append(final_img)
            
    if frames:
        frames[0].save(save_path, save_all=True, append_images=frames[1:], optimize=False, duration=100, loop=0)
        print(f"Saved GIF: {save_path}")

def main():
    root_train = "/media/UbuntuStorage/datasets/FINAL_INDUSTRYSHAPES/hugging_face/IndustryShapes/train"
    root_test = "/media/UbuntuStorage/datasets/FINAL_INDUSTRYSHAPES/hugging_face/IndustryShapes/test"
    
    output_dir = "assets/gallery"
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    
    # 1. Classic Set: Train 1-13 (Exclude 7,8,9), Test 1-8
    classic_scenes = []
    # Train 1-13 excluding 7,8,9
    for i in range(1, 14): 
        if i in [7, 8, 9]: continue
        classic_scenes.append(os.path.join(root_train, f"{i:06d}"))
    
    for i in range(1, 9): classic_scenes.append(os.path.join(root_test, f"{i:06d}"))
    
    # 2. Extended Set: Test 9-11
    extended_scenes = []
    for i in range(9, 12): extended_scenes.append(os.path.join(root_test, f"{i:06d}"))
    
    # Collect pool for Classic
    classic_pool = []
    for sc in classic_scenes:
        imgs = get_image_list(sc)
        if not imgs: continue
        # downsample pool
        for img in imgs[::50]:
            classic_pool.append((sc, img))
            
    # Collect pool for Extended
    extended_pool = []
    for sc in extended_scenes:
        imgs = get_image_list(sc)
        if not imgs: continue
        for img in imgs[::20]: 
            extended_pool.append((sc, img))
            
    # Sample 15 for Classic Gallery (3x5)
    random.seed(42)
    classic_selection = random.sample(classic_pool, min(15, len(classic_pool)))
    
    # Sample 15 for Extended Gallery (3x5)
    extended_selection = random.sample(extended_pool, min(15, len(extended_pool)))
    
    # Process Classic Gallery
    print("Generating Classic Gallery Images...")
    for i, (sc, fname) in enumerate(classic_selection):
        out_name = f"classic_gal_{i+1}.png"
        annotated, _ = render_scene_image(sc, fname)
        if annotated:
            annotated.save(os.path.join(output_dir, out_name))
            
    # Process Extended Gallery
    print("Generating Extended Gallery Images...")
    for i, (sc, fname) in enumerate(extended_selection):
        out_name = f"extended_gal_{i+1}.png"
        annotated, _ = render_scene_image(sc, fname)
        if annotated:
            annotated.save(os.path.join(output_dir, out_name))
            
    # --- Onboarding GIFs (Extended Set) ---
    print("Generating Onboarding GIFs...")
    # Obj1: 15, Obj2: 17, Obj3: 19, Obj4: 21, Obj5: 23
    # Logic: Full around object -> More frames (e.g. 100), skip maybe 5-8?
    # Obj 2 (Scene 17): Cut first 100 frames.
    
    onboarding_indices = [15, 17, 19, 21, 23]
    for idx, scene_idx in enumerate(onboarding_indices):
        scene_path = os.path.join(root_train, f"{scene_idx:06d}")
        if not os.path.exists(scene_path): continue
            
        gif_path = os.path.join(output_dir, f"onboarding_obj_{idx+1}.gif")
        
        start = 0
        if scene_idx == 17: # Obj 2
            start = 100
            
        # Increase frame count for full rotation effect
        generate_gif(scene_path, gif_path, frame_step=8, max_frames=100, start_frame=start)
            
    # --- Slider Cases ---
    print("Generating Slider Images...")
    
    # Case 1: Test Scene 2, Frame 148
    c1_scene = os.path.join(root_test, "000002")
    c1_img = "000148.png"
    if os.path.exists(os.path.join(c1_scene, 'rgb', c1_img)):
        annotated, original = render_scene_image(c1_scene, c1_img)
        annotated.save(os.path.join(output_dir, "slider_1_pose.png"))
        original.save(os.path.join(output_dir, "slider_1_rgb.png"))
        
    # Case 2: Test Scene 3 (Different image)
    c2_scene = os.path.join(root_test, "000003")
    imgs = get_image_list(c2_scene)
    if imgs:
        # Pick 3/4th way through
        c2_img = imgs[int(len(imgs)*0.75)] 
        annotated, original = render_scene_image(c2_scene, c2_img)
        annotated.save(os.path.join(output_dir, "slider_2_pose.png"))
        original.save(os.path.join(output_dir, "slider_2_rgb.png"))
        
    # Case 3: Different Extended Image (Scene 11)
    c3_scene = os.path.join(root_test, "000011") 
    imgs = get_image_list(c3_scene)
    if imgs:
        c3_img = imgs[int(len(imgs)*0.5)] # Middle
        annotated, original = render_scene_image(c3_scene, c3_img)
        annotated.save(os.path.join(output_dir, "slider_3_pose.png"))
        original.save(os.path.join(output_dir, "slider_3_rgb.png"))
    
    print("Done.")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()

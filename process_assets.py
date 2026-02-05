import json
import numpy as np
import os
import math
from PIL import Image, ImageDraw

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

def draw_3d_box(draw, R, t, K, min_pt, max_pt, color=(0, 255, 255), scale=1.0):
    corners_3d = get_box_corners_from_bounds(min_pt, max_pt)
    corners_2d = project_points(corners_3d, R, t, K)
    if corners_2d is None: return

    corners_2d = [(x*scale, y*scale) for x, y in corners_2d]

    edges = [
        (0,1), (1,2), (2,3), (3,0), 
        (4,5), (5,6), (6,7), (7,4), 
        (0,4), (1,5), (2,6), (3,7)  
    ]
    
    width = max(1, int(2 * scale))
    
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
    
    width = max(1, int(3 * scale))
    
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

def render_scene(scene_path, frame_key=None, scale_factor=2):
    global OBJECT_BOUNDS
    if not OBJECT_BOUNDS:
        OBJECT_BOUNDS = load_objects_bounds(MODEL_DIR)

    rgb_dir = os.path.join(scene_path, 'rgb')
    if not os.path.exists(rgb_dir): return None
    
    # Find first PNG
    images = sorted([f for f in os.listdir(rgb_dir) if f.endswith('.png')])
    if not images: return None
    
    # Use the first image if frame_key not specified
    if frame_key is None:
        filename = images[0]
        # Frame key is usually the integer value of the filename without extension
        frame_key = str(int(os.path.splitext(filename)[0]))
    else:
        filename = f"{int(frame_key):06d}.png"
        if not os.path.exists(os.path.join(rgb_dir, filename)):
             # Fallback
             filename = images[0]
             frame_key = str(int(os.path.splitext(filename)[0]))

    rgb_p = os.path.join(rgb_dir, filename)
    gt_p = os.path.join(scene_path, 'scene_gt.json')
    cam_p = os.path.join(scene_path, 'scene_camera.json')
    
    img = Image.open(rgb_p).convert("RGB")
    w, h = img.size
    
    target_w, target_h = int(w * scale_factor), int(h * scale_factor)
    img_large = img.resize((target_w, target_h), resample=Image.BICUBIC)
    draw = ImageDraw.Draw(img_large)
    
    if os.path.exists(gt_p):
        with open(gt_p, 'r') as f: gt_data = json.load(f)
        with open(cam_p, 'r') as f: cam_data = json.load(f)
        
        # Ensure key format matches JSON (sometimes strings "1" sometimes "000001"?)
        # Standard BOP is "1", "2". My previous code used str(int(key)).
        key = str(int(frame_key))
        
        if key in gt_data:
            cam_info = cam_data[key]
            K = np.array(cam_info['cam_K']).reshape(3, 3)
            objects = gt_data[key]
            
            # Standard Green for all boxes to match typical annotations
            colors = [(0, 255, 0)]
            
            for obj in objects:
                obj_id = int(obj['obj_id'])
                R = np.array(obj['cam_R_m2c']).reshape(3, 3)
                t = np.array(obj['cam_t_m2c']).reshape(3, 1)
                
                if obj_id in OBJECT_BOUNDS:
                    min_pt, max_pt = OBJECT_BOUNDS[obj_id]
                    color = colors[0]
                    draw_3d_box(draw, R, t, K, min_pt, max_pt, color=color, scale=scale_factor)
                    draw_axis(draw, R, t, K, length=70, scale=scale_factor)
            
    img_final = img_large.resize((w, h), resample=Image.LANCZOS)
    return img_final

from PIL import Image, ImageDraw, ImageFont

def draw_3d_box(draw, R, t, K, min_pt, max_pt, color=(0, 255, 255), scale=1.0):
    corners_3d = get_box_corners_from_bounds(min_pt, max_pt)
    corners_2d = project_points(corners_3d, R, t, K)
    if corners_2d is None: return

    corners_2d = [(x*scale, y*scale) for x, y in corners_2d]

    edges = [
        (0,1), (1,2), (2,3), (3,0), 
        (4,5), (5,6), (6,7), (7,4), 
        (0,4), (1,5), (2,6), (3,7)  
    ]
    
    # Thicker lines as requested
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
    
    # Super thick for maximum vividness
    width = max(4, int(10 * scale)) 
    
    draw.line([origin, pts_2d[1]], fill=(255, 0, 0), width=width) # X Red
    draw.line([origin, pts_2d[2]], fill=(0, 255, 0), width=width) # Y Green
    draw.line([origin, pts_2d[3]], fill=(0, 0, 255), width=width) # Z Blue

def add_label(draw, text, pos, font_size=30, color=(255, 255, 255)):
    try:
        # Try to load a nicer font
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    draw.text(pos, text, fill=color, font=font)

def create_panel(title, content_img, size):
    # Simplified panel creation
    panel = Image.new('RGBA', size, (20, 25, 40, 230))
    draw = ImageDraw.Draw(panel)
    draw.rectangle([0, 0, size[0]-1, size[1]-1], outline=(100, 100, 100), width=2)
    add_label(draw, title, (20, 15), font_size=28)
    if content_img:
        avail_w = size[0] - 20
        avail_h = size[1] - 60
        cw, ch = content_img.size
        ratio = min(avail_w/cw, avail_h/ch)
        new_size = (int(cw*ratio), int(ch*ratio))
        c_resized = content_img.resize(new_size, Image.LANCZOS)
        x_off = (size[0] - new_size[0]) // 2
        y_off = 60 + (avail_h - new_size[1]) // 2
        panel.paste(c_resized, (x_off, y_off))
    return panel

def generate_gif(scene_path, save_path, frame_step=10, max_frames=80):
    rgb_dir = os.path.join(scene_path, 'rgb')
    if not os.path.exists(rgb_dir): return
    
    files = sorted([f for f in os.listdir(rgb_dir) if f.endswith('.png')])
    frames = []
    count = 0
    
    # Use every Nth frame
    for i in range(0, len(files), frame_step):
        if count >= max_frames: break
        
        f_name = files[i]
        key = str(int(os.path.splitext(f_name)[0]))
        img = render_scene(scene_path, frame_key=key, scale_factor=2.0)
        if img:
            img.thumbnail((640, 640))
            frames.append(img)
            count += 1
            
    if frames:
        frames[0].save(save_path, save_all=True, append_images=frames[1:], optimize=False, duration=100, loop=0)
        print(f"Saved GIF: {save_path}")

def generate_depth_gif(scene_path, save_path, frame_step=10, max_frames=80):
    depth_dir = os.path.join(scene_path, 'depth')
    if not os.path.exists(depth_dir): return
    
    files = sorted([f for f in os.listdir(depth_dir) if f.endswith('.png')])
    frames = []
    count = 0
    
    for i in range(0, len(files), frame_step):
        if count >= max_frames: break
        
        f_name = files[i]
        # Load depth
        d_img = Image.open(os.path.join(depth_dir, f_name))
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
        # Normalize 0..0.33 to 0..1
        t1 = d_norm[mask1] / 0.33
        rgb[mask1, 0] = (t1 * 255).astype(np.uint8)
        
        # 0.33 - 0.66: Red (255,0,0) -> Yellow (255,255,0)
        mask2 = (d_norm >= 0.33) & (d_norm < 0.66)
        t2 = (d_norm[mask2] - 0.33) / 0.33
        rgb[mask2, 0] = 255
        rgb[mask2, 1] = (t2 * 255).astype(np.uint8)
        
        # 0.66 - 1.0: Yellow (255,255,0) -> White (255,255,255)
        mask3 = d_norm >= 0.66
        t3 = (d_norm[mask3] - 0.66) / 0.34 # 0.34 remaining
        rgb[mask3, 0] = 255
        rgb[mask3, 1] = 255
        rgb[mask3, 2] = (t3 * 255).astype(np.uint8)
        
        img = Image.fromarray(rgb, mode='RGB')
        
        if img:
            # Resize
            img.thumbnail((640, 640))
            frames.append(img)
            count += 1
            
    if frames:
        frames[0].save(save_path, save_all=True, append_images=frames[1:], optimize=False, duration=100, loop=0)
        print(f"Saved GIF: {save_path}")

def main():
    root_test = "/media/UbuntuStorage/datasets/FINAL_INDUSTRYSHAPES/hugging_face/IndustryShapes/test"
    root_train = "/media/UbuntuStorage/datasets/FINAL_INDUSTRYSHAPES/hugging_face/IndustryShapes/train"
    
    if not os.path.exists("assets"): os.makedirs("assets")
    
    print("Generating Interactive Assets...")
    
    # 1. Onboarding Rotating GIF (RGB)
    generate_gif(os.path.join(root_train, "000015"), "assets/onboarding_rotate.gif")
    
    # 2. Onboarding Depth GIF
    generate_depth_gif(os.path.join(root_train, "000015"), "assets/onboarding_depth.gif")
    
    print("Assets generated.")

if __name__ == "__main__":
    main()

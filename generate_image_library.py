import os
import shutil
import random
from process_assets import render_scene

# Scene categories mapping
categories = {
    "multi": ["000003"],  # Multiple instances - scene 3
    "occlusion_clutter": ["000004", "000002", "000005", "000006", "000007", "000008"]  # Occlusion and clutter
}

root_test = "/media/UbuntuStorage/datasets/FINAL_INDUSTRYSHAPES/hugging_face/IndustryShapes/test"
out_dir = "assets/real_env"

if not os.path.exists(out_dir): os.makedirs(out_dir)

for category, scenes in categories.items():
    img_count = 0
    for scene_id in scenes:
        scene_path = os.path.join(root_test, scene_id)
        if os.path.exists(scene_path):
            rgb_dir = os.path.join(scene_path, "rgb")
            if os.path.exists(rgb_dir):
                frames = sorted([f for f in os.listdir(rgb_dir) if f.endswith('.png')])
                if frames:
                    # For multi (scene 3), get 4 evenly spaced frames
                    # For occlusion_clutter, get 1 frame per scene
                    if category == "multi":
                        # Get 4 frames from this scene
                        indices = [len(frames) // 5 * i for i in range(1, 5)]
                        for idx in indices:
                            if idx < len(frames):
                                frame_key = str(int(os.path.splitext(frames[idx])[0]))
                                img = render_scene(scene_path, frame_key=frame_key, scale_factor=2.0)
                                if img:
                                    img_count += 1
                                    save_path = os.path.join(out_dir, f"{category}_{img_count}.png")
                                    img.save(save_path)
                                    print(f"Saved {save_path}")
                    else:
                        # Get 1 middle frame from each scene
                        frame_idx = len(frames) // 2
                        frame_key = str(int(os.path.splitext(frames[frame_idx])[0]))
                        img = render_scene(scene_path, frame_key=frame_key, scale_factor=2.0)
                        if img:
                            img_count += 1
                            save_path = os.path.join(out_dir, f"{category}_{img_count}.png")
                            img.save(save_path)
                            print(f"Saved {save_path}")

print("Image library generation complete.")

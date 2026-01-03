"""Create a GIF from DJ Genie screenshots for the README"""
from PIL import Image
import os

# Screenshot folder
screenshots_dir = r"C:\Users\saziz\video-dj-playlist\screenshots"

# Screenshots in order for the GIF
screenshot_files = [
    "01-prompt-entered.png",
    "02-thinking.png",
    "03-playlist-generated.png",
    "05-shoutouts-section.png",
    "06-generating-started.png",
    "09-processing-midway.png",
    "11-processing-85-percent.png",
    "14-mix-complete.png",
]

# Load and resize images
images = []
for filename in screenshot_files:
    filepath = os.path.join(screenshots_dir, filename)
    if os.path.exists(filepath):
        img = Image.open(filepath)
        # Resize to a smaller size for the GIF
        img = img.resize((800, 600), Image.Resampling.LANCZOS)
        images.append(img)
        print(f"Loaded: {filename}")
    else:
        print(f"Missing: {filename}")

if images:
    # Save as GIF with longer duration for each frame
    output_path = os.path.join(screenshots_dir, "dj-genie-demo.gif")
    images[0].save(
        output_path,
        save_all=True,
        append_images=images[1:],
        duration=2000,  # 2 seconds per frame
        loop=0  # Loop forever
    )
    print(f"\nGIF created: {output_path}")
    print(f"Total frames: {len(images)}")
else:
    print("No images found!")

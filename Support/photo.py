import subprocess
import threading
import time
import json
from tqdm import tqdm
import re
from pathlib import Path

support_dir = Path(__file__).parent.resolve()

def show_progress_bar(stop_event):
    with tqdm(total=100, desc="Rendering", bar_format='{l_bar}{bar}| {elapsed}') as pbar:
        while not stop_event.is_set():
            pbar.update(1)
            time.sleep(0.05)
            if pbar.n >= 100:
                pbar.n = 0
                pbar.refresh()

def extract_json_from_output(output):
    match = re.search(r"\{.*\}", output, re.DOTALL)
    if match:
        return json.loads(match.group())
    return None

def run_corner_animation(
    video_path,
    image_path,
    output_path,
    direction,
    duration,
    scale,
    venv_python_path,
    inference_script_path
):
    command = [
        venv_python_path,
        inference_script_path,
        video_path,
        image_path,
        output_path,
        direction,
        str(duration),
        str(scale)
    ]

    stop_event = threading.Event()
    progress_thread = threading.Thread(target=show_progress_bar, args=(stop_event,))
    progress_thread.start()

    try:
        result = subprocess.run(command, capture_output=True, text=True)
    finally:
        stop_event.set()
        progress_thread.join()

    if result.returncode != 0:
        print("\n❌ Error:", result.stderr)
        return None

    parsed = extract_json_from_output(result.stdout)
    if parsed is None:
        print("\n❌ Invalid or missing JSON in output:\n", result.stdout)
        return None

    return parsed

# 🔧 Example usage
if __name__ == "__main__":
    response = run_corner_animation(
        video_path="input_video.mp4",
        image_path="corner_image.png",
        output_path="output_video.mp4",
        direction="right",
        duration=0.3,
        scale=1.75,
        venv_python_path= support_dir / "Photo Adder" / "venv" / "Scripts" / "python.exe",
        inference_script_path= support_dir / "Photo Adder" / "inference.py"
    )

    print("\n✅ Animation complete:", response)

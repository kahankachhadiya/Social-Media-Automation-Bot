import subprocess
import json
import time
import threading
from tqdm import tqdm
import re
from pathlib import Path

support_dir = Path(__file__).parent.resolve()

def show_progress_bar(stop_event):
    with tqdm(total=100, desc="Generating Speech", bar_format='{l_bar}{bar}| {elapsed}') as pbar:
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

def run_speech_synthesis(
    text,
    audio_prompt_path,
    exaggeration,
    temperature,
    seed_num,
    cfg_weight,
    output_path,
    venv_python_path,
    inference_script_path
):
    command = [
        venv_python_path,
        inference_script_path,
        text,
        audio_prompt_path,
        str(exaggeration),
        str(temperature),
        str(seed_num),
        str(cfg_weight),
        output_path
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

    # Extract valid JSON from mixed stdout
    parsed = extract_json_from_output(result.stdout)
    if parsed is None:
        print("\n❌ Invalid or missing JSON in output:\n", result.stdout)
        return None

    return parsed

# Example usage
if __name__ == "__main__":
    response = run_speech_synthesis(
        text="This is a test using subprocess.",
        audio_prompt_path="audio_sample.wav",
        exaggeration=0.6,
        temperature=0.9,
        seed_num=42,
        cfg_weight=0.5,
        output_path="generated_audio.wav",
        venv_python_path= support_dir / "Chatterbox" / "chatterbox_env" / "Scripts" / "python.exe",
        inference_script_path= support_dir / "Chatterbox" / "inference.py"
    )

    print("\n✅ Response from inference.py:", response)

import os
import sys
import shutil
import subprocess
import pandas as pd
from pathlib import Path
from moviepy.editor import AudioFileClip, VideoFileClip
from tqdm import tqdm
import time
from audio import run_speech_synthesis
from photo import run_corner_animation
from subtitle import run_inference_with_progress, burn_subtitles

# === CONFIGURATION ===
AUDIO_VENV = r"D:\Projects\YOUTUBE_VIDEO_CREATION\Chatterbox\chatterbox_env\Scripts\python.exe"
AUDIO_SCRIPT = r"D:\Projects\YOUTUBE_VIDEO_CREATION\Chatterbox\chatterbox\inference.py"

PHOTO_VENV = r"D:\Projects\YOUTUBE_VIDEO_CREATION\PHOTO_ADDITION\venv\Scripts\python.exe"
PHOTO_SCRIPT = r"D:\Projects\YOUTUBE_VIDEO_CREATION\PHOTO_ADDITION\inference.py"

SUBTITLE_INFERENCE = Path(r"D:\Projects\YOUTUBE_VIDEO_CREATION\SUBTITLE_GENERATION\inference.py")

BACKGROUND_VIDEO = Path("video.MP4")
SCRIPT_FILE = Path("script.xlsx")
RESOURCE_DIR = Path("Resource")
TEMP_DIR = Path("temp")
OUTPUT_CLIPS = []

TEMP_DIR.mkdir(exist_ok=True)

# === LOAD SCRIPT ===
df = pd.read_excel(SCRIPT_FILE)
total_steps = len(df)

progress_bar = tqdm(total=total_steps, desc="Processing Dialogues", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')

video_clip_full = VideoFileClip(str(BACKGROUND_VIDEO)).without_audio()
start_time = 0

for idx, row in enumerate(df.itertuples(index=False), start=1):
    print(f"\n--- Processing line {idx} ---")
    text = str(row.Dialogue)
    character = str(row.Character)
    photo_side = str(row.Photo_Side)
    exaggeration = float(row.Exaggeration)
    temperature = float(row.Temperature)
    seed_num = int(row.Seed_num)
    cfg_weight = float(row.Cfg_weight)
    scale = float(row.scale)
    font_size = int(row.FontSize) if hasattr(row, 'FontSize') else 48  # Default to 48

    audio_prompt_path = RESOURCE_DIR / character / f"{character}.wav"
    image_path = RESOURCE_DIR / character / f"{character}.png"
    raw_audio_path = TEMP_DIR / f"audio_{idx}.wav"

    # --- 1. Generate Audio ---
    run_speech_synthesis(
        text=text,
        audio_prompt_path=str(audio_prompt_path),
        exaggeration=exaggeration,
        temperature=temperature,
        seed_num=seed_num,
        cfg_weight=cfg_weight,
        output_path=str(raw_audio_path),
        venv_python_path=AUDIO_VENV,
        inference_script_path=AUDIO_SCRIPT
    )

    # --- 2. Normalize Audio ---
    normalized_audio = TEMP_DIR / f"audio_{idx}_norm.wav"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_audio_path),
        "-af", "loudnorm=I=-16:LRA=11:TP=-1.5",
        str(normalized_audio)
    ], check=True)

    output_audio = normalized_audio

    # --- 3. Trim Background Video ---
    audio_clip = AudioFileClip(str(output_audio))
    actual_audio_duration = audio_clip.duration
    video_duration = actual_audio_duration + 0.5
    end_time = start_time + video_duration

    trimmed_video_path = TEMP_DIR / f"temp_video_{idx}.mp4"
    video_segment = video_clip_full.subclip(start_time, end_time)
    video_segment.write_videofile(str(trimmed_video_path), codec="libx264", audio=False)

    start_time = end_time  # Move start point for next clip

    # --- 4. Generate Subtitles ---
    with open("transcript.txt", "w", encoding="utf-8") as f:
        f.write(text)

    run_inference_with_progress(
        audio_path=str(output_audio),
        transcript_path="transcript.txt",
        inference_script_path=SUBTITLE_INFERENCE
    )

    # Modify subtitle font size in the .ass file
    with open("subtitles.ass", "r", encoding="utf-8") as f:
        ass_data = f.readlines()

    with open("subtitles.ass", "w", encoding="utf-8") as f:
        for line in ass_data:
            if line.strip().startswith("Style:"):
                parts = line.strip().split(",")
                if len(parts) > 3:
                    parts[2] = str(font_size)  # font size field
                f.write(",".join(parts) + "\n")
            else:
                f.write(line)

    karaoke_video = TEMP_DIR / f"karaoke_{idx}.mp4"
    burn_subtitles(
        video_input=str(trimmed_video_path),
        audio_input=str(output_audio),
        ass_subs="subtitles.ass",
        video_output=str(karaoke_video)
    )

    # --- 5. Add Photo Overlay ---
    final_clip = TEMP_DIR / f"clip_{idx}.mp4"
    run_corner_animation(
        video_path=str(karaoke_video),
        image_path=str(image_path),
        output_path=str(final_clip),
        direction=photo_side.lower(),
        duration=0.3,
        scale=scale,
        venv_python_path=PHOTO_VENV,
        inference_script_path=PHOTO_SCRIPT
    )

    OUTPUT_CLIPS.append(final_clip)
    progress_bar.update(1)

progress_bar.close()

# === 6. Merge All Clips ===
with open("file_list.txt", "w") as f:
    for clip in OUTPUT_CLIPS:
        f.write(f"file '{clip.as_posix()}'\n")

subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
    "-i", "file_list.txt", "-c", "copy", "final_output.mp4"
])

print("\n✅ Final video saved as final_output.mp4")

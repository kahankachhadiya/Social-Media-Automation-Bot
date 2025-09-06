import os
import shutil
import subprocess
import pandas as pd
import random
import sys
from pathlib import Path
from moviepy.editor import AudioFileClip, VideoFileClip
from tqdm import tqdm

base_dir = Path(__file__).parent.resolve()
support_dir = base_dir / "Support"

if str(support_dir) not in sys.path:
    sys.path.append(str(support_dir))
    
from .audio import run_speech_synthesis
from .photo import run_corner_animation
from .subtitle import run_inference_with_progress, burn_subtitles

# === FIXED PATHS ===
support_dir = Path(__file__).parent.resolve()

AUDIO_VENV = support_dir / "Chatterbox" / "chatterbox_env" / "Scripts" / "python.exe"
AUDIO_SCRIPT = support_dir / "Chatterbox" / "inference.py"

PHOTO_VENV = support_dir / "Photo Adder" / "venv" / "Scripts" / "python.exe"
PHOTO_SCRIPT = support_dir / "Photo Adder" / "inference.py"

SUBTITLE_INFERENCE = support_dir / "Subtitle Generator" / "inference.py"

# === ✅ Use main.py's folder as base ===
BASE_DIR = Path(sys.argv[0]).parent.resolve()
RESOURCE_DIR = BASE_DIR / "Support" / "Resource"
CHARACTER_DIR = RESOURCE_DIR / "Characters"
VIDEOS_DIR = RESOURCE_DIR / "Videos"
TEMP_DIR = BASE_DIR / "Temporary" / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

def get_random_video() -> Path:
    video_files = list(VIDEOS_DIR.glob("*.*"))
    if not video_files:
        raise FileNotFoundError("❌ No videos found in Resource/Videos/")
    return random.choice(video_files)

def find_valid_excel_file(folder: Path) -> Path:
    excel_files = [f for f in folder.glob("*.xlsx") if not f.name.startswith("~$")]
    if not excel_files:
        raise FileNotFoundError("❌ No valid Excel script file found.")
    return excel_files[0]

def process_video_script(script_path: Path = None):
    if script_path is None or script_path.name.startswith("~$") or not script_path.exists():
        print("🔍 Searching for valid Excel script...")
        script_path = find_valid_excel_file(BASE_DIR)

    script_name = script_path.stem
    print(f"📄 Processing: {script_path.name}")

    # Create dedicated folders
    temp_folder = TEMP_DIR / script_name
    output_folder = BASE_DIR / "outputs" / script_name
    temp_folder.mkdir(parents=True, exist_ok=True)
    output_folder.mkdir(parents=True, exist_ok=True)

    video_path = get_random_video()
    print(f"🎬 Selected Background Video: {video_path.name}")

    df = pd.read_excel(script_path)
    total_steps = len(df)

    progress_bar = tqdm(total=total_steps, desc="Processing Dialogues", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')

    video_clip_full = VideoFileClip(str(video_path)).without_audio()
    start_time = 0
    OUTPUT_CLIPS = []

    for idx, row in enumerate(df.itertuples(index=False), start=1):
        print(f"\n--- Processing line {idx} ---")
        try:
            text = str(row.Dialogue)
            character = str(row.Character)
            photo_side = str(getattr(row, 'Photo_Side', 'left')).lower()
            exaggeration = float(getattr(row, 'Exaggeration', 0.6))
            temperature = float(getattr(row, 'Temperature', 0.7))
            seed_num = int(getattr(row, 'Seed_num', 42))
            cfg_weight = float(getattr(row, 'Cfg_weight', 0.5))
            scale = float(getattr(row, 'scale', 1.25))
            font_size = int(getattr(row, 'FontSize', 48))

            char_path = CHARACTER_DIR / character
            audio_prompt_path = char_path / f"{character}.wav"
            image_path = char_path / f"{character}.png"
            raw_audio_path = temp_folder / f"audio_{idx}.wav"

            # 1. Generate Audio
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

            # 2. Normalize Audio
            normalized_audio = temp_folder / f"audio_{idx}_norm.wav"
            subprocess.run([
                "ffmpeg", "-y", "-i", str(raw_audio_path),
                "-af", "loudnorm=I=-16:LRA=11:TP=-1.5",
                str(normalized_audio)
            ], check=True)

            output_audio = normalized_audio

            # 3. Trim Background Video
            audio_clip = AudioFileClip(str(output_audio))
            actual_audio_duration = audio_clip.duration
            video_duration = actual_audio_duration + 0.5
            end_time = start_time + video_duration

            trimmed_video_path = temp_folder / f"temp_video_{idx}.mp4"
            video_segment = video_clip_full.subclip(start_time, end_time)
            video_segment.write_videofile(str(trimmed_video_path), codec="libx264", audio=False, verbose=False, logger=None)

            start_time = end_time

            # 4. Generate Subtitles
            transcript_file = temp_folder / "transcript.txt"
            with open(transcript_file, "w", encoding="utf-8") as f:
                f.write(text)

            run_inference_with_progress(
                audio_path=str(output_audio),
                transcript_path=str(transcript_file),
                inference_script_path=SUBTITLE_INFERENCE
            )

            ass_file = temp_folder / "subtitles.ass"
            if Path("subtitles.ass").exists():
                shutil.move("subtitles.ass", ass_file)

            # Update font size in ASS
            with open(ass_file, "r", encoding="utf-8") as f:
                ass_data = f.readlines()
            with open(ass_file, "w", encoding="utf-8") as f:
                for line in ass_data:
                    if line.strip().startswith("Style:"):
                        parts = line.strip().split(",")
                        if len(parts) > 3:
                            parts[2] = str(font_size)
                        f.write(",".join(parts) + "\n")
                    else:
                        f.write(line)

            karaoke_video = temp_folder / f"karaoke_{idx}.mp4"
            burn_subtitles(
                video_input=str(trimmed_video_path),
                audio_input=str(output_audio),
                ass_subs=str(ass_file),
                video_output=str(karaoke_video)
            )

            # 5. Add Photo Overlay
            final_clip = temp_folder / f"clip_{idx}.mp4"
            run_corner_animation(
                video_path=str(karaoke_video),
                image_path=str(image_path),
                output_path=str(final_clip),
                direction=photo_side,
                duration=0.3,
                scale=scale,
                venv_python_path=PHOTO_VENV,
                inference_script_path=PHOTO_SCRIPT
            )

            OUTPUT_CLIPS.append(final_clip)
            progress_bar.update(1)

        except Exception as e:
            print(f"❌ Error in line {idx}: {e}")
            progress_bar.update(1)

    progress_bar.close()

    # 6. Merge All Clips
    final_list_path = temp_folder / "file_list.txt"
    with open(final_list_path, "w") as f:
        for clip in OUTPUT_CLIPS:
            f.write(f"file '{clip.as_posix()}'\n")

    final_video_path = output_folder / f"final_output_{script_name}.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(final_list_path), "-c", "copy", str(final_video_path)
    ])

    print(f"\n✅ Final video saved to: {final_video_path}")

import subprocess
import sys
from pathlib import Path
import shlex
import platform

support_dir = Path(__file__).parent.resolve()
INFERENCE_SCRIPT = support_dir / "Subtitle Generator" / "inference.py"

AUDIO = "audio.wav"
TRANSCRIPT = "transcript.txt"
VIDEO = "background.mp4"
OUTPUT_VIDEO = "output_karaoke.mp4"
ASS_FILE = "subtitles.ass"

def run_inference_with_progress(audio_path, transcript_path, inference_script_path):
    cmd = [
        sys.executable,
        str(inference_script_path),
        audio_path,
        transcript_path
    ]
    print("Running alignment + karaoke pipeline...")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")

    for line in process.stdout:
        print(line, end="")

    process.wait()
    if process.returncode != 0:
        raise RuntimeError(f"Inference script failed with code {process.returncode}")

def burn_subtitles(video_input, audio_input, ass_subs, video_output):
    # Use full, absolute path with forward slashes
    safe_ass_path = str(Path(ass_subs).resolve()).replace('\\', '/')

    # On Windows, FFmpeg needs escaping of special characters like colon and space
    if platform.system() == "Windows":
        # Escape colon (:) and space in path for Windows-safe ffmpeg filter
        escaped_path = safe_ass_path.replace(':', '\\:').replace(' ', '\\ ')
    else:
        escaped_path = safe_ass_path  # On Linux/macOS, it's fine as-is

    filter_complex = f"[0:v]ass='{escaped_path}'[v];[1:a]anull[a]"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_input),
        "-i", str(audio_input),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(video_output)
    ]

    print("Running ffmpeg command...\n", " ".join(shlex.quote(arg) for arg in cmd))
    subprocess.run(cmd, check=True)




if __name__ == "__main__":
    try:
        run_inference_with_progress(AUDIO, TRANSCRIPT, INFERENCE_SCRIPT)
        print("Rendering video with karaoke subtitles...")
        burn_subtitles(VIDEO, AUDIO, ASS_FILE, OUTPUT_VIDEO)
        print(f"Done! Video saved as: {OUTPUT_VIDEO}")
    except Exception as e:
        print("Error:", e)

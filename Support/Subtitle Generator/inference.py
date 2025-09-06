import requests
import sys
from tqdm import tqdm

GENTLE_URL = "http://localhost:8765/transcriptions?async=false"

def align_audio_with_gentle(audio_path, transcript_path):
    with open(audio_path, "rb") as audio_file, open(transcript_path, "r", encoding="utf-8") as text_file:
        files = {
            "audio": ("audio.wav", audio_file, "audio/wav"),
            "transcript": ("transcript.txt", text_file, "text/plain")
        }
        response = requests.post(GENTLE_URL, files=files)
        response.raise_for_status()
        return response.json()

def generate_word_by_word_karaoke_ass_subtitles(words, ass_path):
    ass_header = """[Script Info]
Title: Karaoke Word-by-Word
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke, Arial Black, 64, &H00FFFFFF, &H000000FF, &H00000000, &H64000000, 1, 0, 0, 0, 100, 100, 0, 0, 1, 4, 5, 5, 30, 30, 40, 1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def sec_to_timestamp(sec):
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        cs = int((sec % 1) * 100)
        return f"{h}:{m:02}:{s:02}.{cs:02}"

    valid_words = [w for w in words if w.get("case") == "success" and w.get("start") is not None and w.get("end") is not None]
    if not valid_words:
        raise ValueError("No valid words found in alignment")

    lines = [ass_header]

    for w in tqdm(valid_words, desc="Generating word-by-word subtitles"):
        start = w["start"]
        end = w["end"]
        duration_cs = int(round((end - start) * 100))
        word_clean = w["word"].replace("{", "").replace("}", "")

        karaoke_text = f"{{\\k{duration_cs}}}{word_clean}"
        line = f"Dialogue: 0,{sec_to_timestamp(start)},{sec_to_timestamp(end)},Karaoke,,0,0,0,,{karaoke_text}"
        lines.append(line)

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def main(args):
    if len(args) < 2:
        print("Usage: python inference.py <audio.wav> <transcript.txt>")
        sys.exit(1)

    audio_path = args[0]
    transcript_path = args[1]
    ass_path = "subtitles.ass"

    print("Aligning audio with Gentle...")
    alignment = align_audio_with_gentle(audio_path, transcript_path)
    print("Alignment complete. Generating karaoke subtitles...")

    generate_word_by_word_karaoke_ass_subtitles(alignment["words"], ass_path)
    print("Karaoke subtitles generated:", ass_path)

if __name__ == "__main__":
    main(sys.argv[1:])

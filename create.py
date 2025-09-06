import os
import json
import re
import requests
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from tqdm import tqdm
from Support.inference_engine import process_video_script

# Load API keys
load_dotenv(dotenv_path=Path(__file__).parent / "Support" / ".env")
API_KEYS = os.getenv("API_KEYS").split(",")
API_URL = "https://api.together.xyz/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen3-235B-A22B-fp8-tput"

# Folder setup
PROMPT_FOLDER = Path("Support/Resource/test")
TOPIC_FOLDER = Path("Support/Resource/Topics")

# 🔧 Centralized output folder
OUTPUT_ROOT = Path("Temporary")
SCRIPT_FOLDER = OUTPUT_ROOT / "Script"
RAW_OUTPUT_LOGS = OUTPUT_ROOT / "RawOutputs"

# Ensure folders exist
OUTPUT_ROOT.mkdir(exist_ok=True)
SCRIPT_FOLDER.mkdir(exist_ok=True)
RAW_OUTPUT_LOGS.mkdir(exist_ok=True)

# Character-specific visual/voice attributes
character_attributes = {
    "Anime Girl" : {"Exaggeration": 0.6,"Temperature": 0.7,"Seed_num": 42,"Cfg_weight": 0.5,"scale": 1,   "FontSize": 48}
}

key_index = 0
api_key_count = len(API_KEYS)
prompt_files = list(PROMPT_FOLDER.glob("*.txt"))

for prompt_file in tqdm(prompt_files, desc="Processing All", unit="prompt"):
    prompt_name = prompt_file.stem
    topic_file = TOPIC_FOLDER / f"{prompt_name}.csv"

    if not topic_file.exists():
        print(f"⚠️ Skipping {prompt_name}: topic file not found.")
        continue

    try:
        df_topic = pd.read_csv(topic_file, header=None)
        if df_topic.empty:
            print(f"⚠️ Skipping {prompt_name}: topic list is empty.")
            continue
        topic = df_topic.iloc[0, 0]
    except Exception as e:
        print(f"❌ Error reading topic file {topic_file.name}: {str(e)}")
        continue

    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            raw_prompt = f.read()
        prompt = raw_prompt.replace("{topic}", topic)

        attempts = 0
        success = False
        while attempts < api_key_count:
            api_key = API_KEYS[(key_index + attempts) % api_key_count]
            print(f"🔑 Using API Key [{(key_index + attempts) % api_key_count + 1}/{api_key_count}]")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            body = {
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 1.0,
                "top_p": 0.9
            }

            try:
                response = requests.post(API_URL, json=body, headers=headers)
                data = response.json()
                if "choices" not in data:
                    raise ValueError(f"❌ API Error: {data.get('error', {}).get('message', 'No choices returned')}")
                raw_output = data["choices"][0]["message"]["content"]

                cleaned_output = raw_output.strip()
                cleaned_output = re.sub(r"^```(?:json)?\s*", "", cleaned_output)
                cleaned_output = re.sub(r"\s*```$", "", cleaned_output)
                match = re.search(r'\{.*\}', cleaned_output, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    output = json.loads(json_str)
                else:
                    raise ValueError("No valid JSON block found.")

                success = True
                key_index = (key_index + attempts + 1) % api_key_count
                break

            except Exception as e:
                with open(RAW_OUTPUT_LOGS / f"{prompt_name}.txt", "w", encoding="utf-8") as out_file:
                    out_file.write(raw_output if 'raw_output' in locals() else "No response")
                print(f"❌ Attempt with API key {(key_index + attempts) % api_key_count + 1} failed: {str(e)}")
                attempts += 1

        if not success:
            raise ValueError("❌ All API keys failed to produce valid JSON.")

        title = output['title']
        description = output['description']
        tags = output['tags']
        dialogue_data = output['dialogue']

        if not dialogue_data:
            print(f"❌ No dialogue found for {prompt_name}")
            continue

        # Alternate left/right for each line
        sides = ["left", "right"]
        rows = []

        for i, item in enumerate(dialogue_data):
            character = item['character']
            side = sides[i % 2]
            attrs = character_attributes.get(character, {})

            row = {
                'Character': character,
                'Dialogue': item['dialogue'],
                'Photo_Side': side,
                'Title of this video': f'"{title}"' if i == 0 else '',
                'Description': f'"{description}"' if i == 0 else '',
                'Tags': f'"{tags}"' if i == 0 else '',
                'Exaggeration': attrs.get('Exaggeration', ''),
                'Temperature': attrs.get('Temperature', ''),
                'Seed_num': attrs.get('Seed_num', ''),
                'Cfg_weight': attrs.get('Cfg_weight', ''),
                'scale': attrs.get('scale', ''),
                'FontSize': attrs.get('FontSize', '')
            }

            rows.append(row)

        output_file_path = SCRIPT_FOLDER / f"{prompt_name}_script.xlsx"
        pd.DataFrame(rows).to_excel(output_file_path, index=False)

        # Remove used topic
        df_topic = df_topic.drop(index=0)
        df_topic.to_csv(topic_file, index=False, header=False)

        # Generate video
        process_video_script(output_file_path)

    except Exception as e:
        print(f"\n❌ Failed on {prompt_name}: {str(e)}\n")
        with open("failures.log", "a", encoding="utf-8") as f:
            f.write(f"{prompt_name} failed: {str(e)}\n")

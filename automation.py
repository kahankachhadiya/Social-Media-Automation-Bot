import os
import json
import re
import requests
import pandas as pd
import pickle
import shutil
import time
import sys
import subprocess
from dotenv import load_dotenv
from pathlib import Path
from tqdm import tqdm
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from Support.inference_engine import process_video_script
    


# Load API keys
load_dotenv(dotenv_path=Path(__file__).parent / "Support" / ".env")
API_KEYS = os.getenv("API_KEYS").split(",")
API_URL = "https://api.together.xyz/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen3-235B-A22B-fp8-tput"

# Folder setup
BASE_DIR = Path(__file__).parent
SUPPORT_DIR = BASE_DIR / "Support"
CRED_DIR = SUPPORT_DIR / "Credentials"
PROMPT_FOLDER = SUPPORT_DIR / "Resource" / "prompts"
TOPIC_FOLDER = SUPPORT_DIR / "Resource" / "Topics"
OUTPUT_ROOT = BASE_DIR / "Temporary"
SCRIPT_FOLDER = OUTPUT_ROOT / "Script"
RAW_OUTPUT_LOGS = OUTPUT_ROOT / "RawOutputs"
IG_SESSION_FOLDER = CRED_DIR / "ig_sessions"
OUTPUTS_DIR = BASE_DIR / "outputs"

# Character-specific visual/voice attributes
character_attributes = {
    "Anime Girl" : {"Exaggeration": 0.6,"Temperature": 0.7,"Seed_num": 42,"Cfg_weight": 0.5,"scale": 1,   "FontSize": 48}
}

CHANNEL_CONFIG = {
    "Flirty Fox": {
        "client_secret": str(CRED_DIR / "client_secret_channel_name.json"),
        "token_file": str(CRED_DIR / "token_channel_name.pickle"),
        "ig_username": "",
        "ig_password": "",
        "telegram_bot_token": "",
        "telegram_chat_id": ""
    },
}

def ensure_folders():
    OUTPUT_ROOT.mkdir(exist_ok=True)
    SCRIPT_FOLDER.mkdir(exist_ok=True)
    RAW_OUTPUT_LOGS.mkdir(exist_ok=True)
    IG_SESSION_FOLDER.mkdir(parents=True, exist_ok=True)

def retry_delete(path, retries=3):
    for attempt in range(retries):
        try:
            shutil.rmtree(path, ignore_errors=False)
            return
        except Exception:
            time.sleep(2)

def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, data={
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    })

def get_authenticated_youtube_service(client_secret, token_file):
    creds = None
    if os.path.exists(token_file):
        with open(token_file, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret, ["https://www.googleapis.com/auth/youtube.upload"])
            creds = flow.run_local_server(port=0)
        with open(token_file, "wb") as token:
            pickle.dump(creds, token)
    return build("youtube", "v3", credentials=creds)

def upload_to_youtube(youtube, video_path, title, description, tags):
    body = {
        "snippet": {
            "title": title,
            "description": f"{description}\n\n" + ' '.join(f"#{tag}" for tag in tags),
            "tags": tags
        },
        "status": {"privacyStatus": "public"}
    }
    media = MediaFileUpload(str(video_path), resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    print("📤 Uploading to YouTube...")
    with tqdm(total=100, desc="YouTube Upload", unit="%", leave=True) as pbar:
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                pbar.n = int(status.progress() * 100)
                pbar.refresh()
        pbar.n = 100
        pbar.refresh()
    return f"https://www.youtube.com/watch?v={response.get('id')}"

def upload_to_instagram(channel_name, video_path, caption):
    creds = CHANNEL_CONFIG[channel_name]
    username = creds["ig_username"]
    password = creds["ig_password"]
    session_path = IG_SESSION_FOLDER / f"{username}.session"

    cl = Client()
    try:
        if session_path.exists():
            cl.load_settings(str(session_path))
            cl.login(username, password)
        else:
            raise LoginRequired
    except Exception:
        code = input(f"Enter OTP for {username}: ")
        cl.login(username, password, verification_code=code)

    cl.dump_settings(str(session_path))
    print("📤 Uploading to Instagram...")
    with tqdm(total=100, desc="Instagram Upload", unit="%", leave=True) as pbar:
        media = cl.clip_upload(str(video_path), caption=caption)
        for _ in range(20):
            pbar.update(5)
            time.sleep(0.1)
    return f"https://www.instagram.com/reel/{media.code}/"

# MAIN PROCESS
prompt_files = list(PROMPT_FOLDER.glob("*.txt"))
key_index = 0
api_key_count = len(API_KEYS)

for prompt_file in tqdm(prompt_files, desc="Processing All", unit="prompt"):
    ensure_folders()
    prompt_name = prompt_file.stem
    topic_file = TOPIC_FOLDER / f"{prompt_name}.csv"
    if not topic_file.exists():
        continue

    try:
        df_topic = pd.read_csv(topic_file, header=None)
        if df_topic.empty:
            continue
        topic = df_topic.iloc[0, 0]
    except:
        continue

    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read().replace("{topic}", topic)

        success = False
        for attempts in range(api_key_count):
            api_key = API_KEYS[(key_index + attempts) % api_key_count]
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            body = {"model": MODEL_NAME, "messages": [{"role": "user", "content": prompt}], "temperature": 1.0, "top_p": 0.9}

            try:
                response = requests.post(API_URL, json=body, headers=headers)
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                content = re.sub(r"^```(?:json)?|```$", "", content.strip())
                output = json.loads(re.search(r'{.*}', content, re.DOTALL).group(0))
                key_index = (key_index + attempts + 1) % api_key_count
                success = True
                break
            except:
                continue

        if not success:
            continue

        title = output['title']
        description = output['description']
        tags_raw = output['tags']
        dialogue_data = output['dialogue']

        tag_list = [tag.strip().replace("#", "") for tag in tags_raw.split()] if isinstance(tags_raw, str) else tags_raw
        caption = f"{title}\n\n{description}\n\n" + ' '.join(f"#{tag}" for tag in tag_list)

        rows, sides = [], ["left", "right"]
        for i, item in enumerate(dialogue_data):
            character = item['character']
            side = sides[i % 2]
            attrs = character_attributes.get(character, {})
            rows.append({
                'Character': character,
                'Dialogue': item['dialogue'],
                'Photo_Side': side,
                'Title of this video': f'"{title}"' if i == 0 else '',
                'Description': f'"{description}"' if i == 0 else '',
                'Tags': f'"{tags_raw}"' if i == 0 else '',
                **attrs
            })

        script_file = SCRIPT_FOLDER / f"{prompt_name}_script.xlsx"
        pd.DataFrame(rows).to_excel(script_file, index=False)
        df_topic.drop(index=0).to_csv(topic_file, index=False, header=False)

        process_video_script(script_file)

        script_name = f"{prompt_name}_script"
        video_file = OUTPUTS_DIR / script_name / f"final_output_{script_name}.mp4"
        if not video_file.exists():
            continue

        channel_name = prompt_name.replace("_", " ")
        if channel_name not in CHANNEL_CONFIG:
            continue

        creds = CHANNEL_CONFIG[channel_name]
        yt = get_authenticated_youtube_service(creds["client_secret"], creds["token_file"])
        yt_url = upload_to_youtube(yt, video_file, title, description, tag_list)
        ig_url = upload_to_instagram(channel_name, video_file, caption)

        telegram_message = (
            f"✅ Upload Successful\n\n"
            f"🎬 *Title:* {title}\n"
            f"📺 [YouTube]({yt_url})\n"
            f"📷 [Instagram]({ig_url})"
        )
        send_telegram_message(creds["telegram_bot_token"], creds["telegram_chat_id"], telegram_message)

        time.sleep(30)
        retry_delete(OUTPUT_ROOT)

    except Exception as e:
        with open("failures.log", "a", encoding="utf-8") as f:
            f.write(f"{prompt_name} failed: {str(e)}\n")



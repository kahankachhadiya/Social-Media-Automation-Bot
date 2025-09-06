# 📹 Social Media Automation Bot

This project automates **content generation, video creation, and publishing** to **YouTube and Instagram**, with Telegram notifications for updates.  

It integrates:
- **AI-powered script/dialogue generation** (via [Together API](https://api.together.xyz/)).
- **Automated video creation** from generated scripts.
- **YouTube uploads** with metadata (title, description, tags).
- **Instagram Reels uploads** with captions.
- **Telegram notifications** for monitoring successful uploads.
- **Credential/session handling** for smooth re-runs.

---

## 🚀 Features
- ✅ AI-based video script generation using prompts + topics.  
- ✅ Auto video rendering via `process_video_script()`.  
- ✅ Uploads to **YouTube** (public videos).  
- ✅ Uploads to **Instagram Reels**.  
- ✅ Sends a **Telegram message** after each successful upload.  
- ✅ Handles retries, API key rotation, and session persistence.  
- ✅ Structured output folders and cleanup after runs.  

---

## 📂 Project Structure
```
.
├── automation.py               # Main automation script
├── Support/
│   ├── .env                    # API keys & secrets
│   ├── Credentials/            # YouTube & IG credentials
│   ├── Resource/
│   │   ├── prompts/            # Prompt templates (*.txt)
│   │   ├── Topics/             # Topics for each prompt (*.csv)
│   │   ├── BackgroundVideos/   # Background videos for rendering
│   └── inference_engine.py     # Video processing logic
├── outputs/                    # Final rendered videos
├── Temporary/                  # Intermediate files
├── failures.log                # Log of failed runs
```

---

## 🔑 Requirements
- Python **3.9+**
- Google API credentials for YouTube uploads.
- Instagram account credentials.
- Telegram bot token + chat ID.
- Together API key(s) for AI generation.

---

## 📦 Installation
To set up the environment and install all required libraries, please follow the instructions in the [`chatterbox/README.md`](./chatterbox/README.md).  

That guide will walk you through:  
- Creating a virtual environment inside the `chatterbox` folder.  
- Installing all dependencies.  
- Preparing credentials and environment variables.  

---

## ⚙️ Configuration
Edit `CHANNEL_CONFIG` inside `automation.py` to set up your channel(s):

```python
CHANNEL_CONFIG = {
    "Flirty Fox": {
        "client_secret": "Support/Credentials/client_secret_channel.json",
        "token_file": "Support/Credentials/token_channel.pickle",
        "ig_username": "your_ig_username",
        "ig_password": "your_ig_password",
        "telegram_bot_token": "your_bot_token",
        "telegram_chat_id": "your_chat_id"
    },
}
```

---

## ▶️ Usage
1. Add your **prompt files** in `Support/Resource/prompts/`  
   (example provided: `funny_script.txt` with placeholders like `{topic}`).
2. Add corresponding **topic files** in `Support/Resource/Topics/`  
   (example provided: `funny_script.csv` with a list of topics).
3. Add **background videos** in `Support/Resource/BackgroundVideos/`  
   (examples provided in the folder).
4. Run the automation:
   ```bash
   python automation.py
   ```

The script will:
- Use your prompts, topics, and background videos.  
- Generate dialogue/scripts with AI.  
- Render a video.  
- Upload to YouTube & Instagram.  
- Notify via Telegram.  

---

## 🛠 Troubleshooting
- If Instagram login fails, you’ll be prompted for an OTP.  
- Check `failures.log` for errors during processing.  
- If YouTube upload fails, ensure OAuth tokens exist in `Support/Credentials/`.  

---

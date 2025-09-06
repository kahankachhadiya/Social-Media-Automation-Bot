import sys
import json
import torch
import random
import numpy as np
from chatterbox.tts import ChatterboxTTS
import soundfile as sf

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def set_seed(seed: int):
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    random.seed(seed)
    np.random.seed(seed)

def synthesize_speech(text, audio_prompt_path, exaggeration=0.5, temperature=0.8, seed_num=0, cfg_weight=0.5, output_path="output.wav"):
    if seed_num != 0:
        set_seed(seed_num)

    model = ChatterboxTTS.from_pretrained(DEVICE)

    wav = model.generate(
        text,
        audio_prompt_path=audio_prompt_path,
        exaggeration=exaggeration,
        temperature=temperature,
        cfg_weight=cfg_weight,
    )

    audio_np = wav.squeeze(0).numpy()
    sf.write(output_path, audio_np, model.sr)

    return {"status": "success", "output_file": output_path}

if __name__ == "__main__":
    try:
        text = sys.argv[1]
        audio_prompt_path = sys.argv[2]
        exaggeration = float(sys.argv[3])
        temperature = float(sys.argv[4])
        seed_num = int(sys.argv[5])
        cfg_weight = float(sys.argv[6])
        output_path = sys.argv[7]

        result = synthesize_speech(
            text=text,
            audio_prompt_path=audio_prompt_path,
            exaggeration=exaggeration,
            temperature=temperature,
            seed_num=seed_num,
            cfg_weight=cfg_weight,
            output_path=output_path
        )
        print(json.dumps(result))

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

import torch
from chatterbox.tts import ChatterboxTTS

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
model = ChatterboxTTS.from_pretrained(DEVICE)

# Base unit phrase to repeat
base_phrase = "This is a test sentence. "
results = []

for char_len in range(100, 1501, 100):  # Increase by 100 chars each step
    text = base_phrase * (char_len // len(base_phrase))
    try:
        print(f"Testing input length: {len(text)} characters")
        wav = model.generate(
            text,
            audio_prompt_path=None,
            exaggeration=0.5,
            temperature=0.8,
            cfg_weight=0.5,
        )
        print(f"✅ Success at {len(text)} characters\n")
        results.append((len(text), True))
    except Exception as e:
        print(f"❌ Failed at {len(text)} characters — {type(e).__name__}: {str(e)}\n")
        results.append((len(text), False))
        break  # Stop testing after first failure

# Final summary
print("Summary:")
for length, success in results:
    print(f"{length} chars: {'Success' if success else 'Fail'}")

import os
import torch
from TTS.api import TTS

# Set device to CPU
device = "cpu"

# Initialize TTS with XTTS v2 model
print("Loading XTTS v2 model...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

# --- Spurgeon ---
text_spurgeon = (
    "I have gone right to the edge of sin. Some strong temptation has taken hold of both my arms, "
    "so that I could not wrestle with it. I have been dragged, as by an awful satanic power, "
    "to the very edge of some horrid precipice... I have looked down, down, down, and seen my portion. "
    "I quivered on the brink of ruin! A strong arm hath saved me! "
    "Could I have gone so near sin, and yet come back again?! "
    "Yes. I am here... unconsumed... because the Lord changes not."
)
speaker_wav_spurgeon = "seeds/spurgeon/spurgeon_seed.wav"
output_path_spurgeon = "spurgeon_xtts_test.wav"

print(f"Generating audio for Spurgeon...")
tts.tts_to_file(text=text_spurgeon, speaker_wav=speaker_wav_spurgeon, language="en", file_path=output_path_spurgeon)

print("Audio generation complete.")

import os
import torch
from TTS.api import TTS

# Set device to CPU
device = "cpu"

# Initialize TTS with XTTS v2 model
print("Loading XTTS v2 model...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

# --- Müller ---
text_muller = (
    "There was a day when I died. Utterly died. "
    "I died to George Müller. To his opinions, his preferences, his tastes, and his will. "
    "I died to the world—its approval, and its censure. "
    "And since then... I have studied only to show myself approved... unto God."
)
speaker_wav_muller = "seeds/muller/muller_seed.wav"
output_path_muller = "muller_xtts_test.wav"

print(f"Generating audio for Müller...")
tts.tts_to_file(text=text_muller, speaker_wav=speaker_wav_muller, language="en", file_path=output_path_muller)

# --- Wesley ---
text_wesley = (
    "And first, whatsoever else it imply, it is a present salvation. "
    "It is something attainable... yea, actually attained on earth, by those who are partakers of this faith. "
    "Ye are saved... to comprise all in one word... from sin."
)
speaker_wav_wesley = "seeds/wesley/wesley_seed.wav"
output_path_wesley = "wesley_xtts_test.wav"

print(f"Generating audio for Wesley...")
tts.tts_to_file(text=text_wesley, speaker_wav=speaker_wav_wesley, language="en", file_path=output_path_wesley)

print("Audio generation complete.")

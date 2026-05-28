import os
import torch
from TTS.api import TTS

# Set device to CPU
device = "cpu"

# Initialize TTS with XTTS v2 model
# This will download the model on first run
print("Loading XTTS v2 model...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

# Text to generate
text = (
    "Now, what ought men to believe in regard to blessings? Is it a mere... loose idea... "
    "that if a man prays for a specific blessing, God will—by some 'mysterious sovereignty'—give "
    "something or other to him, or perhaps to somebody else, somewhere? "
    "All this is utter NONSENSE! And it is highly dishonorable to God!"
)

# Reference audio (seed)
speaker_wav = "seeds/finney/finney_seed.wav"

# Output file
output_path = "finney_xtts_test.wav"

print(f"Generating audio for: {text[:50]}...")
tts.tts_to_file(
    text=text,
    speaker_wav=speaker_wav,
    language="en",
    file_path=output_path
)

print(f"Audio generated successfully: {output_path}")

import subprocess
import sys
import os
from pathlib import Path

# Configuration
SEED_PATH = 'seeds/spurgeon/spurgeon_seed.wav'
PROMPT_TEXT = 'Welcome to the Metropolitan Tabernacle.' # Fallback if .lab not found
OUTPUT_PATH = 'output/test_f5tts_output.wav'
DEVICE = 'cpu' # Change to cuda if GPU is available
MODEL = 'F5TTS_v1_Base'

# Create output dir if not exists
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

# Test sermon text
sermon_text = """
[solemn]
"NOT UNTO US, O LORD, NOT UNTO US, BUT UNTO THY NAME GIVE GLORY, FOR THY MERCY, AND FOR THY TRUTH'S SAKE." - PSALM 115, verse 1.

Every careful reader can see the connection between this 115th Psalm and the one which precedes it.
"""
sermon_file = Path('test_sermon_text.txt')
sermon_file.write_text(sermon_text.strip())

cmd = [
    sys.executable, '-m', 'f5_tts.infer.infer_cli',
    '--model', MODEL,
    '--ref_audio', SEED_PATH,
    '--ref_text', PROMPT_TEXT,
    '--gen_file', str(sermon_file),
    '--output_file', OUTPUT_PATH,
    '--device', DEVICE,
]

print('🎤 Starting F5-TTS generation on CPU (this might take a while)...')
print('Command:', ' '.join(cmd))

try:
    result = subprocess.run(cmd, check=True)
    print(f'\n✅ Generation complete! Audio saved to {OUTPUT_PATH}')
except subprocess.CalledProcessError as e:
    print(f'❌ Generation failed: {e}')

# Cleanup
if sermon_file.exists():
    sermon_file.unlink()

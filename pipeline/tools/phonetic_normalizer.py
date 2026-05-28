import re

# Dictionary for common biblical book name normalizations
BOOK_NAME_MAP = {
    r"\b1\s*Kings\b": "First Kings",
    r"\b2\s*Kings\b": "Second Kings",
    r"\b1\s*Sam\b\.?": "First Samuel",
    r"\b2\s*Sam\b\.?": "Second Samuel",
    r"\b1\s*Chron\b\.?": "First Chronicles",
    r"\b2\s*Chron\b\.?": "Second Chronicles",
    r"\b1\s*Cor\b\.?": "First Corinthians",
    r"\b2\s*Cor\b\.?": "Second Corinthians",
    r"\b1\s*Thess\b\.?": "First Thessalonians",
    r"\b2\s*Thess\b\.?": "Second Thessalonians",
    r"\b1\s*Tim\b\.?": "First Timothy",
    r"\b2\s*Tim\b\.?": "Second Timothy",
    r"\b1\s*Pet\b\.?": "First Peter",
    r"\b2\s*Pet\b\.?": "Second Peter",
    r"\b1\s*John\b": "First John",
    r"\b2\s*John\b": "Second John",
    r"\b3\s*John\b": "Third John",
    r"\bRev\b\.?": "Revelation",
    r"\bPs\b\.?": "Psalm",
    r"\bGen\b\.?": "Genesis",
    r"\bEx\b\.?": "Exodus",
    r"\bLev\b\.?": "Leviticus",
    r"\bNum\b\.?": "Numbers",
    r"\bDeut\b\.?": "Deuteronomy",
}

# Pronunciation hints for difficult biblical names (phonetic spelling)
PRONUNCIATION_HINTS = {
    "Melchizedek": "Mel-kiz-uh-dek",
    "Nebuchadnezzar": "Neb-uh-kud-nez-er",
    "Mephibosheth": "Me-fib-o-sheth",
    "Capernaum": "Kuh-per-nay-um",
    "Gethsemane": "Geth-sem-uh-nee",
    "Sovereignty": "Sov-rin-tee", # Often mispronounced by TTS
}

def normalize_text(text):
    # 1. Normalize Book Names
    for pattern, replacement in BOOK_NAME_MAP.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # 2. Apply Phonetic Hints
    # We do this carefully to avoid messing up words that contain these strings
    for word, hint in PRONUNCIATION_HINTS.items():
        text = re.sub(rf"\b{re.escape(word)}\b", hint, text, flags=re.IGNORECASE)
        
    return text

if __name__ == "__main__":
    # Quick test
    test_text = "In 2 Kings and 1 Cor, we see Melchizedek and Gethsemane."
    print(f"Original: {test_text}")
    print(f"Normalized: {normalize_text(test_text)}")

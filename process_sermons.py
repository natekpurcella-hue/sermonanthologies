import os
import re

def get_themes(content, title, folder):
    themes_map = {
        "AW Tozer": ["Awe", "Pursuit of God", "Holy Hunger", "Spiritual Life", "Worship"],
        "Charles Spurgeon": ["Sovereignty", "Grace", "Christ-centered", "Faith", "Redemption"],
        "Finney": ["Revival", "Prayer", "Repentance", "Evangelism", "Holy Spirit"],
        "George Muller": ["Faith", "Providence", "Orphans", "Prayer", "Trust"],
        "Ravenhill": ["Judgment", "Eternity", "Prayer", "Holiness", "Revival"],
        "Wesley": ["Holiness", "Grace", "Faith", "Christian Perfection", "Witness of the Spirit"]
    }
    
    base_themes = themes_map.get(folder, ["Faith", "Sermon", "Christianity"])
    
    specific_themes = []
    title_words = title.lower().replace("-", " ").replace("_", " ").split()
    if "prayer" in title_words: specific_themes.append("Prayer")
    if "faith" in title_words: specific_themes.append("Faith")
    if "grace" in title_words: specific_themes.append("Grace")
    if "revival" in title_words: specific_themes.append("Revival")
    if "sin" in title_words: specific_themes.append("Sin")
    if "love" in title_words: specific_themes.append("Love")
    if "judgment" in title_words: specific_themes.append("Judgment")
    if "spirit" in title_words: specific_themes.append("Holy Spirit")
    if "justification" in title_words: specific_themes.append("Justification")
    if "almost" in title_words: specific_themes.append("Almost Christian")
    
    combined = list(dict.fromkeys(specific_themes + base_themes))[:5]
    if len(combined) < 3:
        combined = base_themes[:5]
    return combined

def extract_title(content, filename, folder):
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    
    # If the first line is a # Header we added, skip it and look further
    start_idx = 0
    if lines and lines[0].startswith("#") and (filename.replace(".md", "") in lines[0] or "PREFACE" in lines[0]):
        start_idx = 1
        
    # Look for a real title
    for line in lines[start_idx:start_idx+15]:
        # Skip common headers or metadata
        if line.startswith("SERMON") or line.startswith("LECTURE") or line.startswith("#"):
            continue
        if re.match(r"^[IVXLCDM]+\.", line):
            continue
        if line.startswith("Text.--") or line.startswith("**Scripture:**") or line.startswith("_By grace"):
            continue
        if len(line) > 3 and not line.startswith("**") and not line.startswith("_"):
            # If it's all caps or largely capitalized, it's likely a title
            return line.strip(".").strip()
            
    return filename.replace(".md", "").replace("-", " ").replace("_", " ")

def clean_content(content, folder, filename):
    # Remove any header we might have added
    lines = content.split("\n")
    if lines and lines[0].startswith("# ") and (filename.replace(".md", "") in lines[0] or "PREFACE" in lines[0]):
        content = "\n".join(lines[1:]).strip()

    if folder == "Wesley" and ("Sermon-01" in filename or "Sermon-17" in filename):
        sermon_start = content.find("SERMON")
        if sermon_start != -1:
            content = content[sermon_start:]
    
    if folder == "Finney":
        lines = content.split("\n")
        new_lines = []
        for line in lines:
            if re.match(r"^Lecture [IVXLCDM]+:.*?\d+$", line.strip()):
                continue
            if re.match(r"^[IVXLCDM]+\..*?\d+$", line.strip()):
                continue
            new_lines.append(line)
        content = "\n".join(new_lines)
    
    return content.strip()

def process_folders():
    folders = ["AW Tozer", "Charles Spurgeon", "Finney", "George Muller", "Ravenhill", "Wesley"]
    results = {}

    for folder in folders:
        results[folder] = []
        files = sorted(os.listdir(folder))
        for filename in files:
            if not filename.endswith(".md") or filename == "INDEX.md" or filename == ".gitkeep":
                continue
            
            filepath = os.path.join(folder, filename)
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Clean Content first to remove any bad headers
            cleaned = clean_content(content, folder, filename)
            
            # Extract Title from cleaned content
            title = extract_title(cleaned, filename, folder)
            
            if folder == "Finney":
                title = re.sub(r"\s+\d+$", "", title).strip()
                title = re.sub(r"^Lecture [IVXLCDM]+: ", "", title).strip()

            # Identify Themes
            themes = get_themes(cleaned, title, folder)
            
            # Write back with proper # Header
            with open(filepath, 'w') as f:
                f.write(f"# {title}\n\n" + cleaned)
            
            results[folder].append({
                "Filename": filename,
                "Title": title,
                "Themes": ", ".join(themes),
                "Used in Anthology": "No"
            })
            
    return results

def generate_indices(results):
    for folder, data in results.items():
        if not data:
            continue
        index_path = os.path.join(folder, "INDEX.md")
        with open(index_path, 'w') as f:
            f.write(f"# Index of {folder}\n\n")
            f.write("| Filename | Title | Themes | Used in Anthology |\n")
            f.write("|----------|-------|--------|-------------------|\n")
            for item in data:
                f.write(f"| {item['Filename']} | {item['Title']} | {item['Themes']} | {item['Used in Anthology']} |\n")
        print(f"Generated INDEX.md for {folder} with {len(data)} items.")

if __name__ == "__main__":
    results = process_folders()
    generate_indices(results)

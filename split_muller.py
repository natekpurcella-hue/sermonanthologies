import re
import os

def clean_text(text):
    # Remove Gutenberg header
    start_marker = re.search(r"\*\*\* START OF THE PROJECT GUTENBERG EBOOK.*? \*\*\*", text)
    if start_marker:
        text = text[start_marker.end():]
    
    # Remove Gutenberg footer
    end_marker = re.search(r"END OF THE FIRST PART", text)
    if end_marker:
        text = text[:end_marker.end()]
    
    # Standardize newlines
    text = text.replace('\r\n', '\n')
    
    return text.strip()

def split_narrative(text):
    sections = []
    
    # Define split points with flexible whitespace/newline matching
    # We use re.MULTILINE to match the start of lines if needed, 
    # but re.search with re.DOTALL is often enough if the pattern is unique.
    
    patterns = [
        (r"I was born at Kroppenstaedt", "Early-Life-1805-1825"),
        (r"One Saturday afternoon, about the middle of November 1825", "Conversion-1825-1827"),
        (r"In August, 1827, I heard that the Continental Society", "Call-to-Missions-1827-1829"),
        (r"About the beginning of the next year.*?my fellow students", "Devonshire-Ministry-1830-1832"),
        (r"May 25th, 1832\.", "Bristol-Early-Labours-1832-1834"),
        (r"March 5, 1834\.", "Scriptural-Knowledge-Institution-1834-1835"),
        (r"January 1, 1835\.", "Deepening-Faith-1835"),
        (r"January 1, 1836\.", "Orphan-Work-Establishment-1836"),
        (r"January 2, 1837\.", "Expansion-and-Review-1837")
    ]
    
    indices = []
    for pattern, name in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            print(f"Found match for {name} at {match.start()}")
            indices.append((match.start(), name))
        else:
            print(f"FAILED to find match for {name}")
    
    indices.sort()
    
    for i in range(len(indices)):
        start_idx, name = indices[i]
        end_idx = indices[i+1][0] if i+1 < len(indices) else len(text)
        content = text[start_idx:end_idx].strip()
        sections.append((name, content))
        
    return sections

def main():
    if not os.path.exists("muller_narrative.txt"):
        print("muller_narrative.txt not found")
        return
        
    with open("muller_narrative.txt", "r", encoding="utf-8") as f:
        text = f.read()
    
    cleaned_text = clean_text(text)
    sections = split_narrative(cleaned_text)
    
    target_dir = "/home/nathan/sermons/George Muller/"
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        
    for i, (name, content) in enumerate(sections):
        filename = f"Muller-Narrative-Part1-{i+1:02d}-{name}.md"
        filepath = os.path.join(target_dir, filename)
        
        # Format as Markdown
        md_content = f"# {name.replace('-', ' ')}\n\n{content}"
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"Saved {filepath}")

if __name__ == "__main__":
    main()


import os
import re

def clean_text(text):
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def split_finney_lectures(input_file, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Lectures usually start with "LECTURE I.", "LECTURE II.", etc.
    lecture_pattern = r'\n\s*LECTURE\s+([IVXLCDM]+)\.?\s*\n'
    matches = list(re.finditer(lecture_pattern, content))
    
    print(f"Found {len(matches)} potential lectures.")

    for i in range(len(matches)):
        start_pos = matches[i].start()
        end_pos = matches[i+1].start() if i + 1 < len(matches) else len(content)
        
        lecture_content = content[start_pos:end_pos]
        lecture_num = matches[i].group(1)
        
        # Title extraction: usually the first few lines after the LECTURE line
        lines = [l.strip() for l in lecture_content.strip().split('\n') if l.strip()]
        title = "Untitled"
        if len(lines) > 1:
            # Often there's a title and then a scripture reference. 
            # We'll take the first few lines as the title.
            title = lines[1]
            if len(lines) > 2 and not lines[2].startswith("Text."):
                title += " " + lines[2]

        clean_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
        filename = f"Finney-Revival-Lecture-{i+1:02d}-{clean_title}.md"
        
        output_path = os.path.join(output_dir, filename)
        cleaned_content = clean_text(lecture_content)
        
        with open(output_path, 'w', encoding='utf-8') as f_out:
            # Add a header
            header = f"# Lecture {lecture_num}: {title}\n\n"
            f_out.write(header + cleaned_content)
            
    return len(matches)

if __name__ == "__main__":
    input_file = "/home/nathan/sermons/finney_raw.txt"
    output_dir = "/home/nathan/sermons/Finney"
    count = split_finney_lectures(input_file, output_dir)
    print(f"Total Finney lectures split: {count}")

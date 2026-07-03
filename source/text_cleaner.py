import re

def clean_text(text: str) -> str:
    if not text:
        return ""
        
    # 1. Normalize line endings and tracking carriage returns
    text = text.replace("\r", "\n")
    
    # 2. Fix broken layout space anomalies inside emails or URLs
    text = re.sub(r'([A-Za-z0-9._%+-]+)\s*@\s*([A-Za-z0-9.-]+)', r'\1@\2', text)
    
    # 3. Clean up common floating background artifacts/delimiters
    text = re.sub(r'(?<=\s)[\|¦\._\-•◦▪›]+(?=\s)', ' ', text)
    
    # 4. Collapse trailing repetitive line white-spaces
    lines = []
    for line in text.splitlines():
        line_clean = re.sub(r'\s+', ' ', line).strip()
        if line_clean:
            lines.append(line_clean)
            
    return "\n".join(lines)
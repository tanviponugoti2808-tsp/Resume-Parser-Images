# export_ner_to_excel.py
import spacy
import pandas as pd
from pathlib import Path
from collections import defaultdict

# --- Configuration ---
MODEL_DIR = Path("models/resume_ner")
TEXT_DIR = Path("dataset/new_normalized_text")
OUTPUT_EXCEL = Path("dataset/ner_predictions.xlsx")

def export_to_excel():
    print(f"Loading model from {MODEL_DIR}...")
    try:
        nlp = spacy.load(MODEL_DIR)
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    if not TEXT_DIR.exists():
        print(f"Error: Text directory {TEXT_DIR} not found.")
        return

    all_records = []
    text_files = list(TEXT_DIR.glob("*.txt"))
    
    print(f"Processing {len(text_files)} resumes...")

    for file_path in text_files:
        text = file_path.read_text(encoding="utf-8")
        doc = nlp(text)
        
        # Group extracted entities by their raw AI labels
        extracted_data = defaultdict(list)
        for ent in doc.ents:
            clean_text = ent.text.strip().replace("\n", " ")
            if clean_text not in extracted_data[ent.label_]: 
                extracted_data[ent.label_].append(clean_text)

        # --- MAP AI LABELS TO YOUR EXACT COLUMNS ---
        # We combine TITLE and ORG into "Experience"
        experience_items = extracted_data.get("TITLE", []) + extracted_data.get("ORG", [])
        
        record = {
            "File Name": file_path.name,
            "Name": " | ".join(extracted_data.get("NAME", [])),
            "Email": " | ".join(extracted_data.get("EMAIL", [])),
            "Contact": " | ".join(extracted_data.get("PHONE", [])),
            "Education": " | ".join(extracted_data.get("DEGREE", [])),
            "Experience": " | ".join(experience_items),
            "Skills": " | ".join(extracted_data.get("SKILL", [])),
            "Certification": " | ".join(extracted_data.get("CERTIFICATION", []))
        }
            
        all_records.append(record)

    if not all_records:
        print("No records processed. Exiting.")
        return

    # Convert to a Pandas DataFrame
    df = pd.DataFrame(all_records)
    
    # Ensure exact column ordering
    columns_order = [
        "File Name", "Name", "Email", "Contact", 
        "Education", "Experience", "Skills", "Certification"
    ]
    df = df[columns_order]

    print(f"Exporting data to {OUTPUT_EXCEL}...")
    
    # Save to Excel
    df.to_excel(OUTPUT_EXCEL, index=False, engine='openpyxl')
    
    print("\n" + "="*40)
    print(f"SUCCESS! Cleaned data saved to: {OUTPUT_EXCEL.absolute()}")
    print("="*40)

if __name__ == "__main__":
    export_to_excel()
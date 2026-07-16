import pandas as pd
import re
import json

def analyze_extraction_quality(file_path):
    print(f"Loading {file_path}...\n")
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    total_resumes = len(df)
    print(f"Total Resumes Processed: {total_resumes}\n")
    print("-" * 50)

    # 1. FILL RATE ANALYSIS
    print("1. FILL RATE (Percentage of non-empty fields):")
    expected_columns = ['Name', 'Email', 'Phone', 'Education', 'Experience', 'Summary', 'Skills', 'Certificates']
    
    for col in expected_columns:
        if col in df.columns:
            # Count cells that are not null, not empty strings, and not "Not Found"
            filled_count = df[col].apply(lambda x: pd.notna(x) and str(x).strip() != "" and str(x).strip().lower() != "not found").sum()
            fill_rate = (filled_count / total_resumes) * 100
            print(f"  - {col.ljust(15)}: {fill_rate:>5.1f}% ({filled_count}/{total_resumes})")
        else:
            print(f"  - {col.ljust(15)}: [Column Missing]")

    print("\n" + "-" * 50)
    
    # 2. ANOMALY DETECTION (Rule-based Red Flags)
    print("2. ANOMALY DETECTION (Potential Regex Failures):")
    
    anomalies = {
        "Suspected Location as Experience": 0,
        "Suspected Designation in Certifications": 0,
        "Suspicious Dates in Education (e.g., 1996-1996)": 0,
        "Missing Education (Total blanks)": 0,
        "Missing Experience (Total blanks)": 0
    }

    suspicious_records = []

    for index, row in df.iterrows():
        name = str(row.get('Name', 'Unknown Candidate'))
        
        # --- Experience Anomalies ---
        exp = str(row.get('Experience', ''))
        if pd.isna(row.get('Experience')) or exp.strip() == "" or exp.lower() == "not found":
            anomalies["Missing Experience (Total blanks)"] += 1
        elif len(exp) < 15 and not re.search(r'\d', exp): 
            # If experience is very short and has no dates, it might be a location/name leak
            anomalies["Suspected Location as Experience"] += 1
            suspicious_records.append(f"[Exp Leak] {name}: '{exp}'")

        # --- Education Anomalies ---
        edu = str(row.get('Education', ''))
        if pd.isna(row.get('Education')) or edu.strip() == "":
            anomalies["Missing Education (Total blanks)"] += 1
        else:
            # Look for exact matching years (e.g., 1996 - 1996) which usually indicates a DOB or phone fragment
            if re.search(r'\b(\d{4})\s*-\s*\1\b', edu):
                anomalies["Suspicious Dates in Education (e.g., 1996-1996)"] += 1
                suspicious_records.append(f"[Edu Date Anomaly] {name}: Contains identical year range.")

        # --- Certification Anomalies ---
        certs = str(row.get('Certifications', ''))
        # Look for "Designation:" or job-like strings in certs
        if re.search(r'(?i)\b(designation|role|responsibilities)\b', certs):
            anomalies["Suspected Designation in Certifications"] += 1
            suspicious_records.append(f"[Cert Leak] {name}: Contains designation/role keywords in Certs.")

    for anomaly, count in anomalies.items():
        print(f"  - {anomaly.ljust(48)}: {count} cases")

    print("\n" + "-" * 50)
    
    # 3. SAMPLE OF SUSPICIOUS RECORDS
    print("3. SUSPICIOUS RECORD SAMPLES (First 10):")
    for record in suspicious_records[:10]:
        print(f"  * {record}")
        
    if len(suspicious_records) > 10:
        print(f"  ... and {len(suspicious_records) - 10} more.")

if __name__ == "__main__":
    # Ensure this script is in the same directory as your excel file
    file_name = "dataset/new_resumes.xlsx"
    analyze_extraction_quality(file_name)
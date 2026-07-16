# validate.py - CLEAN VERSION (No Extra Columns, All Fuzzy)
import pandas as pd
import re
from pathlib import Path
from thefuzz import fuzz

# -------------------------------------------------
# Files
# -------------------------------------------------

GENERATED_FILE = "dataset/new_resumes.xlsx"
REFERENCE_FILE = "extracted_data_20260318_125237 (1).xlsx"

generated = pd.read_excel(
    GENERATED_FILE,
    dtype={"Phone": str}
)

reference = pd.read_excel(
    REFERENCE_FILE,
    dtype={"phone_number": str}
)

# -------------------------------------------------
# Filename matching
# -------------------------------------------------

generated["match_name"] = generated["File Name"].astype(str).apply(
    lambda x: Path(x).stem.lower().strip()
)

reference["match_name"] = reference["resume_filename"].astype(str).apply(
    lambda x: Path(x).stem.lower().strip()
)

comparison = pd.merge(
    generated,
    reference,
    on="match_name",
    how="inner"
)

print(f"\n✅ Matched {len(comparison)} resumes\n")


# ============================================================
# NORMALIZATION FUNCTIONS
# ============================================================

def normalize_phone_smart(phone):
    """Fix broken phone format: 83291380(+91-83291) → 83291"""
    if pd.isna(phone):
        return ""
    
    phone_str = str(phone).strip()
    
    # Pattern: "XXXXXXXX(+91-XXXXX)"
    match_broken = re.match(r'^(\d{6,10})\(\+?91-(\d{4,6})\)$', phone_str)
    
    if match_broken:
        return match_broken.group(2)  # Return part after +91-
    
    # Standard formats
    if '+' in phone_str or '-' in phone_str:
        digits = re.sub(r'\D', '', phone_str)
        if len(digits) == 12 and digits.startswith('91'):
            return digits[2:]
        elif len(digits) == 10:
            return digits
        elif len(digits) > 10:
            return digits[-10:]
        return digits
    
    # Pure digits
    digits = re.sub(r'\D', '', phone_str)
    if len(digits) >= 10:
        return digits[-10:]
    elif len(digits) > 0:
        return digits
    
    return ""


def normalize_email_smart(email):
    """Remove duplicates: Lahadeabl Lahadeabl → lahadeabl"""
    if pd.isna(email):
        return ""
    
    email_str = str(email).strip().lower()
    email_str = ' '.join(email_str.split())
    email_str = email_str.rstrip('.,')
    
    # Remove consecutive duplicates
    parts = email_str.split()
    if len(parts) >= 2:
        cleaned = []
        prev = None
        for part in parts:
            if part != prev:
                cleaned.append(part)
                prev = part
        email_str = ' '.join(cleaned)
    
    if '@' in email_str:
        match = re.search(r'[\w.-]+@[\w.-]+\.\w+', email_str)
        if match:
            return match.group(0).lower()
    
    return email_str


def normalize_text(text):
    """Normalize text for fuzzy comparison"""
    if pd.isna(text):
        return ""
    text = str(text).strip().lower()
    text = text.replace("\n", " ")
    text = re.sub(r'\s+', ' ', text)
    return text


# ============================================================
# FUZZY MATCHING FUNCTIONS
# ============================================================

def fuzzy_match(a, b):
    """Basic fuzzy match"""
    if pd.isna(a) and pd.isna(b):
        return 100
    if pd.isna(a) or pd.isna(b):
        return 0
    return fuzz.token_set_ratio(str(a), str(b))


def fuzzy_match_normalized(a, b):
    """Fuzzy match with normalization (for names)"""
    if pd.isna(a) and pd.isna(b):
        return 100
    if pd.isna(a) or pd.isna(b):
        return 0
    
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)
    
    score1 = fuzz.token_set_ratio(a_norm, b_norm)
    score2 = fuzz.token_sort_ratio(a_norm, b_norm)
    score3 = fuzz.partial_ratio(a_norm, b_norm)
    
    return max(score1, score2, score3)


def fuzzy_match_list(a, b):
    """Fuzzy match for lists (skills, certificates)"""
    if pd.isna(a) and pd.isna(b):
        return 100
    if pd.isna(a) or pd.isna(b):
        return 0
    
    list_a = [item.strip().lower() for item in str(a).replace('\n', ',').split(',') if item.strip()]
    list_b = [item.strip().lower() for item in str(b).replace('\n', ',').split(',') if item.strip()]
    
    if not list_a and not list_b:
        return 100
    if not list_a or not list_b:
        return 0
    
    scores = []
    for item_a in list_a:
        best_score = max(fuzz.token_set_ratio(item_a, item_b) for item_b in list_b)
        scores.append(best_score)
    
    return sum(scores) / len(scores) if scores else 0


# ============================================================
# VALIDATION
# ============================================================

print("🔍 Running validation...\n")

# Email Match (with smart normalization)
comparison["Email_Match"] = (
    comparison["Email"].apply(normalize_email_smart) ==
    comparison["email"].apply(normalize_email_smart)
)

# Phone Match (with smart normalization)
comparison["Phone_Match"] = (
    comparison["Phone"].apply(normalize_phone_smart) ==
    comparison["phone_number"].apply(normalize_phone_smart)
)

# Fuzzy Scores
comparison["Name_Score"] = comparison.apply(
    lambda r: fuzzy_match_normalized(r["Name"], r["candidate_name"]),
    axis=1
)

comparison["Education_Score"] = comparison.apply(
    lambda r: fuzzy_match(r["Education"], r["education"]),
    axis=1
)

comparison["Experience_Score"] = comparison.apply(
    lambda r: fuzzy_match(r["Experience"], r["professional_experience"]),
    axis=1
)

comparison["Skills_Score"] = comparison.apply(
    lambda r: fuzzy_match_list(r["Skills"], r["technical_skills"]),
    axis=1
)

comparison["Certificates_Score"] = comparison.apply(
    lambda r: fuzzy_match_list(r["Certificates"], r["certifications"]),
    axis=1
)


# ============================================================
# REPORT
# ============================================================

print("\n" + "=" * 70)
print("📊 ACCURACY REPORT")
print("=" * 70)

print(f"\nMatched Resumes              : {len(comparison)}")
print("-" * 70)

print(f"\nExact Matches:")
print(f"   Phone Accuracy               : {comparison['Phone_Match'].mean()*100:.2f}%")
print(f"   Email Accuracy               : {comparison['Email_Match'].mean()*100:.2f}%")

print(f"\nFuzzy Similarity:")
print(f"   Name Similarity              : {comparison['Name_Score'].mean():.2f}%")
print(f"   Education Similarity         : {comparison['Education_Score'].mean():.2f}%")
print(f"   Experience Similarity        : {comparison['Experience_Score'].mean():.2f}%")
print(f"   Skills Similarity            : {comparison['Skills_Score'].mean():.2f}%")
print(f"   Certificate Similarity       : {comparison['Certificates_Score'].mean():.2f}%")

overall = (
    comparison["Email_Match"].mean() * 100 +
    comparison["Phone_Match"].mean() * 100 +
    comparison["Name_Score"].mean() +
    comparison["Education_Score"].mean() +
    comparison["Experience_Score"].mean() +
    comparison["Skills_Score"].mean() +
    comparison["Certificates_Score"].mean()
) / 7

print(f"\n" + "=" * 70)
print(f"Overall Extraction Accuracy     : {overall:.2f}%")
print("=" * 70)


# ============================================================
# SAVE TO EXACT SAME FORMAT AS BEFORE
# ============================================================

report = comparison[[
    "File Name",
    "Name",
    "candidate_name",
    "Name_Score",
    "Email",
    "email",
    "Email_Match",
    "Phone",
    "phone_number",
    "Phone_Match",
    "Education",
    "education",
    "Education_Score",
    "Experience",
    "professional_experience",
    "Experience_Score",
    "Skills",
    "technical_skills",
    "Skills_Score",
    "Certificates",
    "certifications",
    "Certificates_Score"
]]

# Save to ORIGINAL filename (no "IMPROVED" suffix!)
report.to_excel("resume_validation_report.xlsx", index=False)

print(f"\n💾 Saved: resume_validation_report.xlsx")
print("=" * 70)
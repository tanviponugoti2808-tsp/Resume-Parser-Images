 
import json
import re
from ollama import chat
 
MODEL = "qwen3:8b"
 
SYSTEM_PROMPT = """/no_think
You are a resume field extractor. You receive raw OCR text from a resume and output ONLY a valid JSON object.
 
OUTPUT FORMAT — return exactly this structure, nothing else:
{
  "name": "full name of the candidate",
  "email": "email address or empty string",
  "phone": "phone number digits only or empty string",
  "summary": "professional summary or objective paragraph, or empty string",
  "skills": ["skill1", "skill2"],
  "experience": [
    {
      "company": "company name",
      "designation": "job title",
      "duration": "date range e.g. Jan 2020 - Mar 2022",
      "responsibilities": ["responsibility 1", "responsibility 2"]
    }
  ],
  "education": [
    {
      "degree": "degree name",
      "college": "college or institution name",
      "university": "university name if different from college",
      "year": "graduation year",
      "cgpa": "cgpa or percentage or empty string"
    }
  ],
  "languages": ["English", "Hindi"],
  "certifications": ["certification 1", "certification 2"]
}
 
STRICT RULES:
- Output ONLY the JSON object. No explanation, no markdown, no code blocks, no preamble.
- Do not invent any information not present in the text.
- If a field is not found, use empty string "" or empty list [].
- name: the candidate's full name, usually at the top of the resume.
- skills: extract actual skill names/tools/technologies written in the resume.
- experience: one entry per job. Extract company, title, dates, and bullet responsibilities.
- education: one entry per qualification.
- certifications: only actual certifications/courses, not job responsibilities.
- languages: only human languages (English, Hindi, etc.), not programming languages.
""" 
def extract_resume_fields(ocr_text: str) -> dict:
    """
    Send OCR text to Qwen3:8b and get back structured resume fields.
    Returns a dict. Falls back to empty structure on any error.
    """
    if not ocr_text or not ocr_text.strip():
        return _empty_result()
 
    try:
        response = chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": ocr_text.strip()}
            ],
            think=False
        )
 
        raw = response["message"]["content"].strip()
 
        # Strip markdown code fences if model wraps in ```json ... ```
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE)
        raw = raw.strip()
 
        # Strip any /think tags the model might emit despite instructions
        raw = re.sub(r'</?think>', '', raw, flags=re.IGNORECASE).strip()
        raw = raw.replace("/think", "").strip()
 
        # Find the JSON object in the response (in case there's any stray text)
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not json_match:
            print(f"  [qwen_extractor] No JSON found in model response")
            return _empty_result()
 
        parsed = json.loads(json_match.group())
        return _normalize(parsed)
 
    except json.JSONDecodeError as e:
        print(f"  [qwen_extractor] JSON parse error: {e}")
        return _empty_result()
    except Exception as e:
        print(f"  [qwen_extractor] Error: {e}")
        return _empty_result()
 
 
def _normalize(parsed: dict) -> dict:
    """Ensure all expected keys exist with correct types."""
    return {
        "name":           str(parsed.get("name", "") or ""),
        "email":          str(parsed.get("email", "") or ""),
        "phone":          str(parsed.get("phone", "") or ""),
        "summary":        str(parsed.get("summary", "") or ""),
        "skills":         _to_list_of_str(parsed.get("skills", [])),
        "experience":     _normalize_experience(parsed.get("experience", [])),
        "education":      _normalize_education(parsed.get("education", [])),
        "languages":      _to_list_of_str(parsed.get("languages", [])),
        "certifications": _to_list_of_str(parsed.get("certifications", [])),
    }
 
 
def _to_list_of_str(val) -> list:
    if isinstance(val, list):
        return [str(x) for x in val if x]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []
 
 
def _normalize_experience(val) -> list:
    if not isinstance(val, list):
        return []
    result = []
    for item in val:
        if not isinstance(item, dict):
            continue
        result.append({
            "company":          str(item.get("company", "") or ""),
            "designation":      str(item.get("designation", "") or ""),
            "duration":         str(item.get("duration", "") or ""),
            "responsibilities": _to_list_of_str(item.get("responsibilities", [])),
        })
    return result
 
 
def _normalize_education(val) -> list:
    if not isinstance(val, list):
        return []
    result = []
    for item in val:
        if not isinstance(item, dict):
            continue
        result.append({
            "degree":     str(item.get("degree", "") or ""),
            "college":    str(item.get("college", "") or ""),
            "university": str(item.get("university", "") or ""),
            "year":       str(item.get("year", "") or ""),
            "cgpa":       str(item.get("cgpa", "") or ""),
        })
    return result
 
 
def _empty_result() -> dict:
    return {
        "name": "", "email": "", "phone": "", "summary": "",
        "skills": [], "experience": [], "education": [],
        "languages": [], "certifications": [],
    }
from ollama import chat

MODEL = "qwen3:8b"

SYSTEM_PROMPT = """
You are an OCR Resume Reconstruction Engine.

Your ONLY task is to reconstruct noisy OCR text into a clean, logically ordered resume.
  
STRICT RULES

- Never invent information.
- Never remove information.
- Preserve every fact present in the OCR.
- Correct only obvious OCR mistakes.

Examples of OCR mistakes you SHOULD correct:
- ATSTICAL → STATISTICAL
- SAIN GANI -> SANGANI
- SHA RMA -> SHARMA
- KUMA R -> KUMAR
- RAVI KUMA R -> RAVI KUMAR
- If two adjacent uppercase words together clearly form a common surname or full name, merge them.
- Apply this only when it is an obvious OCR word split.
- Do not invent names
- qmail.com → gmail.com if it is clearly an OCR error.
- GmaiI.com → gmail.com (capital I mistaken for l).
- gmai1.com → gmail.com (digit 1 mistaken for l).
- hotmaiI.com → hotmail.com.

For email addresses:
- Correct only obvious OCR errors in common domains (gmail.com, outlook.com, yahoo.com, hotmail.com, icloud.com).
- Do NOT change the username before the @ unless it is an obvious OCR split or merge.
- Do NOT invent an email address.

Also:
- Merge wrapped lines into complete sentences.
- Keep company names with job titles and dates.
- Reconstruct logical resume sections:
  Name
  Contact
  Summary
  Skills
  Work Experience
  Education
  Certifications
  Languages
  Projects
- Preserve bullet points.
- Never remove standalone lines that appear between the candidate's name and contact details, as they are often the candidate's professional title (e.g., Statistical Programmer, Software Engineer, Data Scientist). Preserve these lines exactly.
- Reconstruct the resume into the most logical order.
- If OCR has mixed two-column content, restore the original reading order.
- Move the candidate's name to the top.
- Keep contact details immediately below the name.
- Group Work Experience together.
- Group Education together.
- Group Skills together.
- Preserve every piece of information.
- Correct obvious OCR spelling mistakes.
- Do not invent information.
- Preserve dates exactly as written.
- Return ONLY plain text.
- Do NOT return JSON.
- Do NOT explain your changes.
- Do NOT output markdown.
"""


def normalize_resume(ocr_text: str) -> str:

    response = chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": ocr_text
            }
        ],
        think=False
    )

    text = response["message"]["content"]

    # Safety cleanup in case the model emits a marker
    text = text.replace("/think", "").strip()

    return text
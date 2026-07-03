import json
from pathlib import Path

from schema import get_empty_resume


def build_resume_json(
    file_name,
    name="",
    email="",
    phone="",
    overall_experience="",
    summary="",
    skills=None,
    education=None,
    experience=None,
    certifications=None,
    languages=None,
    projects=None,
    achievements=None,
):

    resume = get_empty_resume()

    resume["file_name"] = file_name
    resume["name"] = name
    resume["email"] = email
    resume["phone"] = phone
    resume["overall_experience"] = overall_experience
    resume["summary"] = summary

    resume["skills"] = skills or []

    resume["education"] = education or []

    resume["experience"] = experience or []

    resume["certifications"] = certifications or []

    resume["languages"] = languages or []

    resume["projects"] = projects or []

    resume["achievements"] = achievements or []

    return resume


def save_resume_json(resume_json, output_folder):

    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    filename = (
        Path(resume_json["file_name"]).stem.replace(" ", "_") + ".json"
    )

    output_file = output_folder / filename

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(resume_json, f, indent=4, ensure_ascii=False)

    print(f"Saved -> {output_file}")
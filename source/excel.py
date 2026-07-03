import json
import glob
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

HEADER_FONT = Font(bold=True, color="FFFFFF", name="Arial")
HEADER_FILL = PatternFill("solid", start_color="4472C4")
BODY_FONT = Font(name="Arial")
WRAP = Alignment(wrap_text=True, vertical="top")
TOP = Alignment(vertical="top")


def load_records(path_or_glob):
    """Load one or more resume JSON files. Accepts a directory, a glob
    pattern, or a single .json file. Also tolerates a file that contains
    multiple concatenated JSON objects."""
    if os.path.isdir(path_or_glob):
        files = sorted(glob.glob(os.path.join(path_or_glob, "*.json")))
    else:
        files = sorted(glob.glob(path_or_glob))

    records = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            content = fh.read().strip()
        decoder = json.JSONDecoder()
        idx = 0
        while idx < len(content):
            sub = content[idx:].lstrip()
            if not sub:
                break
            idx += len(content[idx:]) - len(sub)
            obj, end = decoder.raw_decode(content, idx)
            records.append(obj)
            idx = end
    return records


def _join(values, sep="; "):
    if not values:
        return ""
    return sep.join(str(v) for v in values if v not in (None, ""))


def _style_header(ws, headers):
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = "A2"


def _autofit(ws, widths):
    for col_idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width


def build_workbook(records, output_path):
    wb = Workbook()

    ws_cand = wb.active
    ws_cand.title = "Candidates"
    cand_headers = [
        "File Name", "Name", "Email", "Phone", "LinkedIn", "Location",
        "Overall Experience", "Summary", "Skills", "Languages", "Achievements",
    ]
    _style_header(ws_cand, cand_headers)

    ws_edu = wb.create_sheet("Education")
    edu_headers = ["Candidate", "File Name", "Degree", "Institution",
                   "Start Year", "End Year", "Additional Info"]
    _style_header(ws_edu, edu_headers)

    ws_exp = wb.create_sheet("Experience")
    exp_headers = ["Candidate", "File Name", "Company", "Designation",
                   "Start Date", "End Date", "Responsibilities"]
    _style_header(ws_exp, exp_headers)

    ws_cert = wb.create_sheet("Certificates")
    cert_headers = ["Candidate", "File Name", "Certification",
                    "Issuing Organization", "Year"]
    _style_header(ws_cert, cert_headers)

    for rec in records:
        file_name = rec.get("file_name", "")
        name = rec.get("name", "")

        ws_cand.append([
            file_name, name, rec.get("email", ""), rec.get("phone", ""),
            rec.get("linkedin", ""), rec.get("location", ""),
            rec.get("overall_experience", ""), rec.get("summary", ""),
            _join(rec.get("skills")), _join(rec.get("languages")),
            _join(rec.get("achievements")),
        ])
        r = ws_cand.max_row
        for c in range(1, len(cand_headers) + 1):
            cell = ws_cand.cell(row=r, column=c)
            cell.font = BODY_FONT
            cell.alignment = WRAP if c in (8, 9, 10, 11) else TOP

        for edu in rec.get("education", []) or []:
            ws_edu.append([
                name, file_name, edu.get("Degree", ""), edu.get("Institution", ""),
                edu.get("Start Year", ""), edu.get("End Year", ""),
                edu.get("Additional_Info", edu.get("Additional Info", "")),
            ])
            r = ws_edu.max_row
            for c in range(1, len(edu_headers) + 1):
                ws_edu.cell(row=r, column=c).font = BODY_FONT
                ws_edu.cell(row=r, column=c).alignment = TOP

        for exp in rec.get("experience", []) or []:
            responsibilities = exp.get("Responsibilities", [])
            cleaned = [str(x).lstrip("> ").strip() for x in responsibilities]
            ws_exp.append([
                name, file_name, exp.get("Company", ""), exp.get("Designation", ""),
                exp.get("Start Date", ""), exp.get("End Date", ""),
                _join(cleaned, sep="\n"),
            ])
            r = ws_exp.max_row
            for c in range(1, len(exp_headers) + 1):
                ws_exp.cell(row=r, column=c).font = BODY_FONT
                ws_exp.cell(row=r, column=c).alignment = WRAP if c == 7 else TOP
            ws_exp.row_dimensions[r].height = min(15 * max(len(cleaned), 1), 300)

        for cert in rec.get("certificates", []) or []:
            ws_cert.append([
                name, file_name, cert.get("Certification", ""),
                cert.get("Issuing_Organization", cert.get("Issuing Organization", "")),
                cert.get("Year", ""),
            ])
            r = ws_cert.max_row
            for c in range(1, len(cert_headers) + 1):
                ws_cert.cell(row=r, column=c).font = BODY_FONT
                ws_cert.cell(row=r, column=c).alignment = WRAP if c == 3 else TOP

    _autofit(ws_cand, [22, 20, 28, 16, 22, 18, 14, 40, 30, 18, 30])
    _autofit(ws_edu, [20, 22, 22, 32, 12, 12, 30])
    _autofit(ws_exp, [20, 22, 30, 24, 14, 14, 60])
    _autofit(ws_cert, [20, 22, 40, 28, 10])

    for ws in (ws_cand, ws_edu, ws_exp, ws_cert):
        if ws.max_row > 1:
            ws.auto_filter.ref = f"A1:{get_column_letter(ws.max_column)}{ws.max_row}"

    wb.save(output_path)
    return output_path
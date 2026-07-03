import json
from pathlib import Path

PREDICTED_DIR = Path("dataset/output_json")
GROUND_TRUTH_DIR = Path("dataset/ground_truth")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_value(field, pred, gt):

    if pred == gt:
        print(f"✅ {field}")
        return 1

    print(f"\n❌ {field}")
    print("Predicted :")
    print(pred)
    print("\nGround Truth :")
    print(gt)

    return 0


def evaluate_resume(filename):

    pred_file = PREDICTED_DIR / filename
    gt_file = GROUND_TRUTH_DIR / filename

    if not pred_file.exists():
        return

    if not gt_file.exists():
        return

    pred = load_json(pred_file)
    gt = load_json(gt_file)

    print("\n")
    print("=" * 70)
    print(filename)
    print("=" * 70)

    score = 0
    total = 0

    fields = [
        "name",
        "email",
        "phone",
        "overall_experience",
        "summary",
        "education",
        "experience",
        "skills",
        "certificates",
        "languages",
        "projects",
        "achievements"
    ]

    for field in fields:

        total += 1

        score += compare_value(
            field,
            pred.get(field),
            gt.get(field)
        )

    accuracy = (score / total) * 100

    print("\n")
    print("-" * 70)
    print(f"Accuracy : {accuracy:.2f}%")
    print("-" * 70)

    return accuracy


def main():

    filename = "Amit Resume.json"

    evaluate_resume(filename)


if __name__ == "__main__":
    main()
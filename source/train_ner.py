# train_ner.py
import json
import random
import spacy
from spacy.training import Example
from pathlib import Path

TRAINING_FILE = Path("dataset/ner_training_data.jsonl")
MODEL_OUTPUT = Path("models/resume_ner")


def load_training_data():
    examples = []
    with open(TRAINING_FILE, encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            entities = [tuple(e) for e in data["entities"]]
            examples.append((data["text"], {"entities": entities}))
    return examples


def train():
    data = load_training_data()
    print(f"Loaded {len(data)} training examples")

    # Split: 90% train, 10% held out for a quick eyeball check later
    random.shuffle(data)
    split_idx = int(len(data) * 0.9)
    train_data = data[:split_idx]
    holdout_data = data[split_idx:]
    print(f"Training on {len(train_data)}, holding out {len(holdout_data)} for review")

    nlp = spacy.blank("en")
    ner = nlp.add_pipe("ner")

    labels = set()
    for _, ann in train_data:
        for _, _, label in ann["entities"]:
            labels.add(label)
    for label in labels:
        ner.add_label(label)

    print(f"Labels: {sorted(labels)}")

    optimizer = nlp.begin_training()

    n_epochs = 40
    for epoch in range(n_epochs):
        random.shuffle(train_data)
        losses = {}

        for text, annotations in train_data:
            doc = nlp.make_doc(text)
            example = Example.from_dict(doc, annotations)
            nlp.update([example], sgd=optimizer, losses=losses, drop=0.3)

        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"Epoch {epoch + 1}/{n_epochs} — Loss: {losses.get('ner', 0):.4f}")

    MODEL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nlp.to_disk(MODEL_OUTPUT)
    print(f"\nModel saved -> {MODEL_OUTPUT}")

    # Quick sanity check on holdout examples
    print("\n--- Holdout sample predictions ---")
    for text, _ in holdout_data[:3]:
        doc = nlp(text)
        print(f"\nText snippet: {text[:80]}...")
        for ent in doc.ents:
            print(f"  {ent.label_}: {ent.text}")


if __name__ == "__main__":
    train()
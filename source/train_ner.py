# train_ner.py
import json
import random
import spacy
from spacy.training import Example
from spacy.scorer import Scorer
from spacy.util import minibatch, compounding
from pathlib import Path

TRAINING_FILE = Path("dataset/ner_training_data.jsonl")
MODEL_OUTPUT = Path("models/resume_ner")
MODEL_OUTPUT_FINAL = Path("models/resume_ner_final")  # last-epoch model, for comparison

N_EPOCHS = 60          # raised ceiling since early stopping will cut it short anyway
PATIENCE = 8           # stop if holdout F1 doesn't improve for this many epochs
DROPOUT = 0.3


def load_training_data():
    examples = []
    with open(TRAINING_FILE, encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            entities = [tuple(e) for e in data["entities"]]
            examples.append((data["text"], {"entities": entities}))
    return examples


# ---------------------------------------------------------------
# CHANGED: build the ner pipe with an explicit tok2vec architecture
# that uses Mish activation in its window encoder, instead of
# spaCy's default Maxout encoder. Mish is a smoother, self-gated
# nonlinearity (x * tanh(softplus(x))) that tends to give better
# gradient flow than Maxout on small datasets -- a reasonable,
# real lever to try given you have ~80 resumes, not thousands.
# ---------------------------------------------------------------
NER_CONFIG = {
    "model": {
        "@architectures": "spacy.TransitionBasedParser.v2",
        "state_type": "ner",
        "extra_state_tokens": False,
        "hidden_width": 64,
        "maxout_pieces": 2,
        "use_upper": True,
        "nO": None,
        "tok2vec": {
            "@architectures": "spacy.Tok2Vec.v2",
            "embed": {
                "@architectures": "spacy.MultiHashEmbed.v2",
                "width": 96,
                "attrs": ["NORM", "PREFIX", "SUFFIX", "SHAPE"],
                "rows": [5000, 2500, 2500, 2500],
                "include_static_vectors": False,
            },
            "encode": {
                # THIS is the activation-function swap:
                # spacy.MaxoutWindowEncoder.v2 (default) -> spacy.MishWindowEncoder.v2
                "@architectures": "spacy.MishWindowEncoder.v2",
                "width": 96,
                "window_size": 1,
                "depth": 4,
            },
        },
    }
}


def build_nlp(labels):
    nlp = spacy.blank("en")
    ner = nlp.add_pipe("ner", config=NER_CONFIG)
    for label in labels:
        ner.add_label(label)
    return nlp


def evaluate_model(nlp, data):
    """Real precision/recall/F1 per label -- this is what you should
    actually trust, not the training loss number."""
    examples = []
    for text, annotations in data:
        doc_gold = nlp.make_doc(text)
        example = Example.from_dict(doc_gold, annotations)
        example.predicted = nlp(text)
        examples.append(example)

    scorer = Scorer()
    scores = scorer.score(examples)
    return scores


def print_scores(scores, header="Scores"):
    print(f"\n--- {header} ---")
    print(f"Overall  P={scores['ents_p']:.3f}  R={scores['ents_r']:.3f}  F={scores['ents_f']:.3f}")
    print("Per label:")
    per_type = scores.get("ents_per_type") or {}
    for label, s in sorted(per_type.items()):
        print(f"  {label:15s} P={s['p']:.3f}  R={s['r']:.3f}  F={s['f']:.3f}")


def train():
    data = load_training_data()
    print(f"Loaded {len(data)} training examples")

    random.shuffle(data)
    split_idx = int(len(data) * 0.9)
    train_data = data[:split_idx]
    holdout_data = data[split_idx:]
    print(f"Training on {len(train_data)}, holding out {len(holdout_data)} for evaluation")

    labels = set()
    for _, ann in train_data:
        for _, _, label in ann["entities"]:
            labels.add(label)
    labels = sorted(labels)
    print(f"Labels: {labels}")

    nlp = build_nlp(labels)
    optimizer = nlp.initialize()

    best_f1 = -1.0
    epochs_without_improvement = 0

    for epoch in range(N_EPOCHS):
        random.shuffle(train_data)
        losses = {}

        # CHANGED: minibatching instead of updating one example at a time.
        # Batch sizes ramp from 4 up to 32 -- small batches early on give
        # more frequent, noisier updates while the model is still learning
        # basic patterns; larger batches later stabilize training.
        batch_sizes = compounding(4.0, 32.0, 1.001)
        batches = minibatch(train_data, size=batch_sizes)

        for batch in batches:
            examples = [
                Example.from_dict(nlp.make_doc(text), ann)
                for text, ann in batch
            ]
            nlp.update(examples, sgd=optimizer, losses=losses, drop=DROPOUT)

        # CHANGED: evaluate on real holdout F1 every epoch instead of
        # just watching the loss number.
        scores = evaluate_model(nlp, holdout_data)
        f1 = scores["ents_f"]

        print(f"Epoch {epoch + 1}/{N_EPOCHS} — Loss: {losses.get('ner', 0):.4f}  Holdout F1: {f1:.4f}")

        if f1 > best_f1:
            best_f1 = f1
            epochs_without_improvement = 0
            MODEL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            nlp.to_disk(MODEL_OUTPUT)  # save BEST checkpoint, not just whatever epoch you stop on
            print(f"  -> New best F1 ({f1:.4f}), checkpoint saved.")
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= PATIENCE:
                print(f"\nEarly stopping at epoch {epoch + 1} (no improvement for {PATIENCE} epochs)")
                print(f"Best holdout F1 achieved: {best_f1:.4f}")
                break

    # Also save the final-epoch model separately, purely so you can compare
    # "best" vs "last" if you want to sanity-check the early stopping decision.
    MODEL_OUTPUT_FINAL.parent.mkdir(parents=True, exist_ok=True)
    nlp.to_disk(MODEL_OUTPUT_FINAL)

    print(f"\nBest model saved  -> {MODEL_OUTPUT}")
    print(f"Final model saved -> {MODEL_OUTPUT_FINAL}")

    # -----------------------------------------------------------
    # Final report: load back the BEST checkpoint (not the last-epoch
    # in-memory model) and score it properly, plus show a few real
    # predictions so you can eyeball quality, not just numbers.
    # -----------------------------------------------------------
    best_nlp = spacy.load(MODEL_OUTPUT)
    final_scores = evaluate_model(best_nlp, holdout_data)
    print_scores(final_scores, header="FINAL holdout scores (best checkpoint)")

    print("\n--- Holdout sample predictions (best checkpoint) ---")
    for text, _ in holdout_data[:3]:
        doc = best_nlp(text)
        print(f"\nText snippet: {text[:80]}...")
        for ent in doc.ents:
            print(f"  {ent.label_}: {ent.text}")


if __name__ == "__main__":
    train()
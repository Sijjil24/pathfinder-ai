"""Role prediction. Uses the TensorFlow model if trained; otherwise falls back to
simple skill-overlap scoring so the app still runs."""
import csv, json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE, "data", "roles_skills.csv")
MODEL_PATH = os.path.join(BASE, "model", "career_model.keras")
META_PATH = os.path.join(BASE, "model", "meta.json")

_model = None
_meta = None


def _load_roles():
    roles = {}
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            roles[row["role"]] = {
                "skills": [s.strip().lower() for s in row["skills"].split(";") if s.strip()],
                "interests": [s.strip().lower() for s in row["interests"].split(";") if s.strip()],
            }
    return roles


ROLES = _load_roles()


def normalize(text):
    return sorted({t.strip().lower() for t in text.replace("\n", ",").split(",") if t.strip()})


def _load_model():
    global _model, _meta
    if _model is None and os.path.exists(MODEL_PATH) and os.path.exists(META_PATH):
        import tensorflow as tf
        _model = tf.keras.models.load_model(MODEL_PATH)
        with open(META_PATH, encoding="utf-8") as f:
            _meta = json.load(f)
    return _model


def _scores_tf(tokens):
    import numpy as np
    model = _load_model()
    index = {t: i for i, t in enumerate(_meta["vocab"])}
    v = np.zeros((1, len(index)), dtype="float32")
    for t in tokens:
        if t in index:
            v[0, index[t]] = 1.0
    probs = model.predict(v, verbose=0)[0]
    return dict(zip(_meta["roles"], [float(p) for p in probs]))


def _scores_overlap(tokens):
    scores = {}
    for role, d in ROLES.items():
        pool = set(d["skills"]) | set(d["interests"])
        scores[role] = len(pool & set(tokens)) / max(len(pool), 1)
    total = sum(scores.values()) or 1
    return {r: s / total for r, s in scores.items()}


def predict_roles(skills_text, interests_text, top_n=3):
    skills = normalize(skills_text)
    interests = normalize(interests_text)
    tokens = skills + interests
    scores = _scores_tf(tokens) if _load_model() else _scores_overlap(tokens)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    results = []
    for role, score in ranked:
        needed = ROLES[role]["skills"]
        results.append({
            "role": role,
            "score": round(score * 100, 1),
            "have": [s for s in needed if s in skills],
            "gaps": [s for s in needed if s not in skills],
        })
    return results

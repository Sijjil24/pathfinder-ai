"""Train a small TensorFlow model that maps skills/interests -> job role.
Run once:  python model/train.py
Everything here is free: TensorFlow + a CSV you can edit and extend."""
import csv, json, os, random
import numpy as np
import tensorflow as tf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE, "data", "roles_skills.csv")
MODEL_PATH = os.path.join(BASE, "model", "career_model.keras")
META_PATH = os.path.join(BASE, "model", "meta.json")

random.seed(42)
np.random.seed(42)

roles, tokens_by_role = [], {}
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        roles.append(row["role"])
        toks = row["skills"].split(";") + row["interests"].split(";")
        tokens_by_role[row["role"]] = [t.strip().lower() for t in toks if t.strip()]

vocab = sorted({t for toks in tokens_by_role.values() for t in toks})
index = {t: i for i, t in enumerate(vocab)}


def encode(tokens):
    v = np.zeros(len(vocab), dtype="float32")
    for t in tokens:
        if t in index:
            v[index[t]] = 1.0
    return v


# Create synthetic training profiles: a random subset of a role's tokens + a little noise.
X, y = [], []
for ri, role in enumerate(roles):
    own = tokens_by_role[role]
    for _ in range(400):
        k = random.randint(2, min(7, len(own)))
        sample = random.sample(own, k)
        sample += random.sample(vocab, random.randint(0, 2))  # noise
        X.append(encode(sample))
        y.append(ri)

X, y = np.array(X), np.array(y)
perm = np.random.permutation(len(X))
X, y = X[perm], y[perm]

model = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(len(vocab),)),
    tf.keras.layers.Dense(64, activation="relu"),
    tf.keras.layers.Dropout(0.3),
    tf.keras.layers.Dense(32, activation="relu"),
    tf.keras.layers.Dense(len(roles), activation="softmax"),
])
model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
model.fit(X, y, epochs=40, batch_size=32, validation_split=0.15, verbose=2)

model.save(MODEL_PATH)
with open(META_PATH, "w", encoding="utf-8") as f:
    json.dump({"vocab": vocab, "roles": roles}, f, indent=2)
print("Saved model to", MODEL_PATH)

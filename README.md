# PathFinder AI - AI Career Path Recommender

Suggests job roles and a free learning path from skills and interests, and tracks progress over time.
Free stack: Python, Flask, TensorFlow, Groq free API, SQLite, Firebase (free plan).

## Run it (Windows)
1. Extract the zip.
2. Double-click **setup.bat** (first time only). It installs Python 3.12 if needed, creates the venv, installs libraries, asks for your Groq key, trains the model and starts the site.
3. Next times, double-click **run.bat**.
4. Open http://localhost:5000

## Turn on Google sign-in + forgot-password emails (free)
1. Go to console.firebase.google.com and create a project (turn Analytics off).
2. Build > Authentication > Get started > enable **Email/Password** and **Google**.
3. Project settings > Your apps > add a **Web app** (</>) and copy the config.
4. Paste into `.env`: FIREBASE_API_KEY, FIREBASE_AUTH_DOMAIN, FIREBASE_PROJECT_ID, FIREBASE_APP_ID.
5. Run **run.bat** again and open http://localhost:5000 (use `localhost`, not 127.0.0.1).

Without Firebase, sign-up and log-in still work with email and password stored (hashed) in SQLite.

## Project layout
- `app.py` routes and auth, `services/` ML + AI logic, `model/train.py` TensorFlow training
- `data/roles_skills.csv` edit roles, then retrain
- `templates/`, `static/` pages, CSS, JS

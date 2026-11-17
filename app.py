import functools, os, re, sqlite3
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
from services.ai_service import generate_plan
from services.ml_service import predict_roles

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or "dev-secret-change-me"
app.config.update(SESSION_COOKIE_SAMESITE="Lax", PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30)
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.db")

FIREBASE = {
    "apiKey": os.getenv("FIREBASE_API_KEY", ""),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", ""),
    "projectId": os.getenv("FIREBASE_PROJECT_ID", ""),
    "appId": os.getenv("FIREBASE_APP_ID", ""),
}
FIREBASE_ON = all(FIREBASE.values())

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, pw_hash TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS profiles(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, skills TEXT, interests TEXT,
  summary TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS recs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER, role TEXT, score REAL, why TEXT, gaps TEXT);
CREATE TABLE IF NOT EXISTS steps(
  id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id INTEGER, position INTEGER, title TEXT,
  description TEXT, weeks INTEGER, done INTEGER DEFAULT 0, done_at TEXT);
"""

SKILL_CHIPS = ["python", "sql", "html", "css", "javascript", "git", "excel", "pandas", "tensorflow",
               "machine learning", "linux", "docker", "figma", "react", "networking", "aws"]
INTEREST_CHIPS = ["ai", "web", "data", "security", "design", "mobile", "cloud", "testing"]


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def init_db():
    with sqlite3.connect(DB) as conn:
        conn.executescript(SCHEMA)


@app.before_request
def load_user():
    g.user = None
    uid = session.get("uid")
    if uid:
        g.user = db().execute("SELECT id,name,email FROM users WHERE id=?", (uid,)).fetchone()


@app.context_processor
def inject():
    return dict(user=g.get("user"), firebase_on=FIREBASE_ON, firebase_config=FIREBASE)


def login_required(view):
    @functools.wraps(view)
    def wrapped(*a, **kw):
        if not g.user:
            flash("Please log in first.", "info")
            return redirect(url_for("login", next=request.path))
        return view(*a, **kw)
    return wrapped


def safe_next(n):
    return n if n and n.startswith("/") and not n.startswith("//") else url_for("dashboard")


def progress(pid):
    row = db().execute("SELECT COUNT(*) t, COALESCE(SUM(done),0) d FROM steps WHERE profile_id=?", (pid,)).fetchone()
    return round(100 * row["d"] / row["t"]) if row["t"] else 0


# ---------- public pages ----------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")


# ---------- auth ----------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if g.user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "")
        if not name or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) or len(pw) < 6:
            flash("Enter your name, a valid email and a password of 6+ characters.", "error")
        elif db().execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            flash("That email already has an account. Try logging in.", "error")
        else:
            cur = db().execute("INSERT INTO users(name,email,pw_hash,created_at) VALUES(?,?,?,?)",
                               (name, email, generate_password_hash(pw), datetime.now().isoformat(timespec="seconds")))
            db().commit()
            session.permanent = True
            session["uid"] = cur.lastrowid
            flash(f"Welcome, {name}! Your account is ready.", "success")
            return redirect(url_for("dashboard"))
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))
    nxt = request.values.get("next", "")
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "")
        row = db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if row and not row["pw_hash"]:
            flash("This account uses Google sign-in. Click 'Continue with Google'.", "info")
        elif row and check_password_hash(row["pw_hash"], pw):
            session.permanent = True
            session["uid"] = row["id"]
            return redirect(safe_next(nxt))
        else:
            flash("Wrong email or password.", "error")
    return render_template("login.html", next=nxt)


@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":  # only reached when Firebase is not set up
        flash("Password reset emails need Firebase. See the README to turn it on (free).", "info")
    return render_template("forgot.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


@app.post("/auth/firebase")
def auth_firebase():
    if not FIREBASE_ON:
        return jsonify(error="Firebase is not set up."), 400
    data = request.get_json(silent=True) or {}
    try:
        from google.auth.transport import requests as greq
        from google.oauth2 import id_token
        claims = id_token.verify_firebase_token(data.get("idToken", ""), greq.Request(), audience=FIREBASE["projectId"])
    except Exception as e:
        print("Firebase verify error:", e)
        claims = None
    if not claims or not claims.get("email"):
        return jsonify(error="Could not verify your sign-in. Please try again."), 401
    email = claims["email"].lower()
    name = claims.get("name") or data.get("name") or email.split("@")[0]
    row = db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if row:
        uid = row["id"]
    else:
        uid = db().execute("INSERT INTO users(name,email,pw_hash,created_at) VALUES(?,?,?,?)",
                           (name, email, "", datetime.now().isoformat(timespec="seconds"))).lastrowid
        db().commit()
    session.permanent = True
    session["uid"] = uid
    return jsonify(ok=True, next=safe_next(data.get("next", "")))


# ---------- app pages ----------
@app.route("/dashboard")
@login_required
def dashboard():
    rows = db().execute("""
        SELECT p.*, (SELECT COUNT(*) FROM steps s WHERE s.profile_id=p.id) total,
               (SELECT COALESCE(SUM(done),0) FROM steps s WHERE s.profile_id=p.id) done,
               (SELECT role FROM recs r WHERE r.profile_id=p.id ORDER BY score DESC LIMIT 1) top_role
        FROM profiles p WHERE p.user_id=? ORDER BY p.id DESC""", (g.user["id"],)).fetchall()
    plans = [dict(r, pct=round(100 * r["done"] / r["total"]) if r["total"] else 0) for r in rows]
    total = sum(p["total"] for p in plans)
    done = sum(p["done"] for p in plans)
    stats = dict(plans=len(plans), done=done, overall=round(100 * done / total) if total else 0)
    return render_template("dashboard.html", plans=plans, stats=stats)


@app.route("/new")
@login_required
def new_plan():
    return render_template("new.html", skill_chips=SKILL_CHIPS, interest_chips=INTEREST_CHIPS)


@app.route("/recommend", methods=["POST"])
@login_required
def recommend():
    name = request.form.get("name", "").strip() or g.user["name"]
    skills = request.form.get("skills", "").strip()
    interests = request.form.get("interests", "").strip()
    if not skills:
        flash("Add at least one skill, separated by commas.", "error")
        return redirect(url_for("new_plan"))
    roles = predict_roles(skills, interests)
    plan_data = generate_plan(name, skills, interests, roles)
    conn = db()
    pid = conn.execute("INSERT INTO profiles(user_id,name,skills,interests,summary,created_at) VALUES(?,?,?,?,?,?)",
                       (g.user["id"], name, skills, interests, plan_data.get("summary", ""),
                        datetime.now().isoformat(timespec="seconds"))).lastrowid
    why = {str(r.get("title", "")).lower(): r for r in plan_data.get("roles", [])}
    for r in roles:
        extra = why.get(r["role"].lower(), {})
        conn.execute("INSERT INTO recs(profile_id,role,score,why,gaps) VALUES(?,?,?,?,?)",
                     (pid, r["role"], r["score"], extra.get("why", ""), ", ".join(r["gaps"][:6])))
    for i, s in enumerate(plan_data.get("steps", []), 1):
        try:
            weeks = int(s.get("weeks") or 1)
        except (TypeError, ValueError):
            weeks = 1
        conn.execute("INSERT INTO steps(profile_id,position,title,description,weeks) VALUES(?,?,?,?,?)",
                     (pid, i, s.get("title", ""), s.get("description", ""), weeks))
    conn.commit()
    return redirect(url_for("plan", pid=pid))


@app.route("/plan/<int:pid>")
@login_required
def plan(pid):
    p = db().execute("SELECT * FROM profiles WHERE id=? AND user_id=?", (pid, g.user["id"])).fetchone()
    if not p:
        flash("Plan not found.", "error")
        return redirect(url_for("dashboard"))
    recs = db().execute("SELECT * FROM recs WHERE profile_id=? ORDER BY score DESC", (pid,)).fetchall()
    steps = db().execute("SELECT * FROM steps WHERE profile_id=? ORDER BY position", (pid,)).fetchall()
    return render_template("plan.html", p=p, recs=recs, steps=steps, progress=progress(pid))


@app.post("/step/<int:sid>/toggle")
@login_required
def toggle(sid):
    conn = db()
    s = conn.execute("""SELECT s.* FROM steps s JOIN profiles p ON p.id=s.profile_id
                        WHERE s.id=? AND p.user_id=?""", (sid, g.user["id"])).fetchone()
    if not s:
        return jsonify(error="not found"), 404
    done = 0 if s["done"] else 1
    stamp = datetime.now().strftime("%d %b %Y")
    conn.execute("UPDATE steps SET done=?, done_at=? WHERE id=?", (done, stamp if done else None, sid))
    conn.commit()
    return jsonify(done=done, progress=progress(s["profile_id"]), done_at=stamp if done else "")


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)

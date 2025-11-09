import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"  # replace with env var in production

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "health.db")

# ------------------------------
# Database functions
# ------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db:
        db.close()

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                water REAL,
                steps INTEGER,
                sleep REAL,
                mood INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        conn.commit()

# ------------------------------
# Routes
# ------------------------------
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_pw = generate_password_hash(password)
        try:
            db = get_db()
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
            db.commit()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return "Username already exists!"
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = get_db().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        return "Invalid credentials!"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

# ------------------------------
# API Routes
# ------------------------------
@app.route("/api/add", methods=["POST"])
def add_entry():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 403
    data = request.get_json()
    db = get_db()
    db.execute(
        "INSERT INTO health (user_id, date, water, steps, sleep, mood) VALUES (?, ?, ?, ?, ?, ?)",
        (session["user_id"], datetime.now().strftime("%Y-%m-%d"), data["water"], data["steps"], data["sleep"], data["mood"])
    )
    db.commit()
    return jsonify({"success": True})

@app.route("/api/data")
def get_data():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 403
    db = get_db()
    rows = db.execute(
        "SELECT date, water, steps, sleep, mood FROM health WHERE user_id=? ORDER BY date",
        (session["user_id"],)
    ).fetchall()
    return jsonify([dict(r) for r in rows])

# ------------------------------
# Run App
# ------------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)

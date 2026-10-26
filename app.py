import os
import random
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, session, flash

BASE_DIR = Path(__file__).resolve().parent
DATABASE = os.environ.get("DATABASE_PATH", str(BASE_DIR / "game.db"))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")

CHOICES = ["rock", "paper", "scissors"]
BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    Path(DATABASE).parent.mkdir(parents=True, exist_ok=True)
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_choice TEXT NOT NULL,
                computer_choice TEXT NOT NULL,
                result TEXT NOT NULL,
                played_at TEXT NOT NULL
            )
        """)
        conn.commit()


def decide_result(player, computer):
    if player == computer:
        return "draw"
    if BEATS[player] == computer:
        return "win"
    return "loss"


@app.route("/")
def index():
    with get_db_connection() as conn:
        history = conn.execute(
            "SELECT player_choice, computer_choice, result, played_at "
            "FROM game_history ORDER BY id DESC LIMIT 10"
        ).fetchall()
        totals = conn.execute("""
            SELECT
                COUNT(*) AS games,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS wins,
                SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) AS losses,
                SUM(CASE WHEN result = 'draw' THEN 1 ELSE 0 END) AS draws
            FROM game_history
        """).fetchone()

    stats = {
        "games": totals["games"] or 0,
        "wins": totals["wins"] or 0,
        "losses": totals["losses"] or 0,
        "draws": totals["draws"] or 0,
    }
    return render_template("index.html", history=history, stats=stats)


@app.route("/play", methods=["POST"])
def play():
    player_choice = request.form.get("choice", "").lower().strip()
    if player_choice not in CHOICES:
        flash("Please choose rock, paper, or scissors.", "error")
        return redirect(url_for("index"))

    computer_choice = random.choice(CHOICES)
    result = decide_result(player_choice, computer_choice)
    played_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO game_history (player_choice, computer_choice, result, played_at) "
            "VALUES (?, ?, ?, ?)",
            (player_choice, computer_choice, result, played_at),
        )
        conn.commit()

    session["last_round"] = {
        "player": player_choice,
        "computer": computer_choice,
        "result": result,
    }
    return redirect(url_for("index"))


@app.route("/reset-history", methods=["POST"])
def reset_history():
    with get_db_connection() as conn:
        conn.execute("DELETE FROM game_history")
        conn.commit()
    session.pop("last_round", None)
    flash("Game history has been cleared.", "success")
    return redirect(url_for("index"))


@app.context_processor
def inject_last_round():
    return {"last_round": session.get("last_round")}


@app.get("/health")
def health():
    return {"status": "ok"}, 200


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)

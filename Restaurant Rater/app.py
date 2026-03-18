import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, g, render_template, request, redirect, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "restaurants.db"

app = Flask(__name__)

# ---------- Database helpers ----------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            cuisine TEXT
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants (id)
        );
        """
    )
    db.commit()

@app.before_first_request
def setup():
    init_db()

# ---------- Routes ----------

@app.route("/")
def index():
    db = get_db()
    restaurants = db.execute(
        "SELECT r.id, r.name, r.address, r.cuisine, "
        "AVG(rv.rating) AS avg_rating, COUNT(rv.id) AS review_count "
        "FROM restaurants r "
        "LEFT JOIN reviews rv ON r.id = rv.restaurant_id "
        "GROUP BY r.id "
        "ORDER BY r.name"
    ).fetchall()
    return render_template("index.html", restaurants=restaurants)

@app.route("/restaurants/new", methods=["GET", "POST"])
def add_restaurant():
    if request.method == "POST":
        name = request.form["name"].strip()
        address = request.form.get("address", "").strip()
        cuisine = request.form.get("cuisine", "").strip()

        if name:
            db = get_db()
            db.execute(
                "INSERT INTO restaurants (name, address, cuisine) VALUES (?, ?, ?)",
                (name, address, cuisine),
            )
            db.commit()
            return redirect(url_for("index"))

    return render_template("add_restaurant.html")

@app.route("/restaurants/<int:restaurant_id>", methods=["GET", "POST"])
def restaurant_detail(restaurant_id):
    db = get_db()

    if request.method == "POST":
        rating = int(request.form["rating"])
        notes = request.form.get("notes", "").strip()
        created_at = datetime.utcnow().isoformat(timespec="seconds")

        db.execute(
            "INSERT INTO reviews (restaurant_id, rating, notes, created_at) "
            "VALUES (?, ?, ?, ?)",
            (restaurant_id, rating, notes, created_at),
        )
        db.commit()
        return redirect(url_for("restaurant_detail", restaurant_id=restaurant_id))

    restaurant = db.execute(
        "SELECT * FROM restaurants WHERE id = ?", (restaurant_id,)
    ).fetchone()

    if restaurant is None:
        return "Restaurant not found", 404

    reviews = db.execute(
        "SELECT * FROM reviews WHERE restaurant_id = ? ORDER BY created_at DESC",
        (restaurant_id,),
    ).fetchall()

    return render_template(
        "restaurant_detail.html",
        restaurant=restaurant,
        reviews=reviews,
    )

if __name__ == "__main__":
    app.run(debug=True)

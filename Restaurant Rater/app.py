import os
import random
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "restaurant_rater.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

POPULAR_CUISINES = [
    "American",
    "BBQ",
    "Breakfast / Brunch",
    "Burgers",
    "Chinese",
    "French",
    "Greek",
    "Indian",
    "Italian",
    "Japanese",
    "Korean",
    "Mediterranean",
    "Mexican",
    "Middle Eastern",
    "Pizza",
    "Seafood",
    "Soul Food",
    "Spanish",
    "Sushi",
    "Thai",
    "Vietnamese",
    "Other"
]


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def column_exists(conn, table_name, column_name):
    columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    column_names = [column["name"] for column in columns]
    return column_name in column_names


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            dishes_tried TEXT,
            rating REAL NOT NULL,
            image_filename TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            rating INTEGER NOT NULL,
            image_filename TEXT
        )
    """)

    # Add dishes_tried column if the table already existed from an older version
    if not column_exists(conn, "restaurants", "dishes_tried"):
        cursor.execute("ALTER TABLE restaurants ADD COLUMN dishes_tried TEXT")

    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = get_db_connection()
    restaurants = conn.execute("SELECT * FROM restaurants ORDER BY id DESC").fetchall()
    recipes = conn.execute("SELECT * FROM recipes ORDER BY id DESC").fetchall()
    conn.close()

    highlight_options = []

    for restaurant in restaurants:
        if restaurant["image_filename"]:
            highlight_options.append({
                "id": restaurant["id"],
                "name": restaurant["name"],
                "category": restaurant["category"],
                "description": restaurant["description"],
                "dishes_tried": restaurant["dishes_tried"],
                "rating": restaurant["rating"],
                "image_filename": restaurant["image_filename"],
                "type": "restaurant"
            })

    for recipe in recipes:
        if recipe["image_filename"]:
            highlight_options.append({
                "id": recipe["id"],
                "name": recipe["name"],
                "description": recipe["description"],
                "rating": recipe["rating"],
                "image_filename": recipe["image_filename"],
                "type": "recipe"
            })

    highlight = random.choice(highlight_options) if highlight_options else None

    return render_template(
        "index.html",
        restaurants=restaurants,
        recipes=recipes,
        highlight=highlight
    )


@app.route("/add_restaurant", methods=["GET", "POST"])
def add_restaurant():
    if request.method == "POST":
        name = request.form["name"].strip()
        category = request.form["category"].strip()
        description = request.form["description"].strip()
        dishes_tried = request.form["dishes_tried"].strip()
        rating_raw = request.form["rating"].strip()

        try:
            rating = float(rating_raw)
        except ValueError:
            flash("Please enter a valid rating.")
            return redirect(request.url)

        if rating < 1 or rating > 10:
            flash("Restaurant rating must be between 1 and 10.")
            return redirect(request.url)

        # Round to 1 decimal place so values stay neat
        rating = round(rating, 1)

        file = request.files.get("image")
        filename = None

        if file and file.filename:
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            else:
                flash("Invalid image file type. Please upload png, jpg, jpeg, or gif.")
                return redirect(request.url)

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO restaurants (name, category, description, dishes_tried, rating, image_filename)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, category, description, dishes_tried, rating, filename)
        )
        conn.commit()
        conn.close()

        flash("Restaurant added successfully!")
        return redirect(url_for("index"))

    return render_template("add_restaurant.html", cuisines=POPULAR_CUISINES)


@app.route("/restaurant/<int:restaurant_id>")
def restaurant_detail(restaurant_id):
    conn = get_db_connection()
    restaurant = conn.execute(
        "SELECT * FROM restaurants WHERE id = ?",
        (restaurant_id,)
    ).fetchone()
    conn.close()

    if restaurant is None:
        flash("Restaurant not found.")
        return redirect(url_for("index"))

    return render_template("restaurant_detail.html", restaurant=restaurant)


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form["description"].strip()
        rating = request.form["rating"]

        file = request.files.get("image")
        filename = None

        if file and file.filename:
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            else:
                flash("Invalid image file type. Please upload png, jpg, jpeg, or gif.")
                return redirect(request.url)

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO recipes (name, description, rating, image_filename)
            VALUES (?, ?, ?, ?)
            """,
            (name, description, rating, filename)
        )
        conn.commit()
        conn.close()

        flash("Recipe added successfully!")
        return redirect(url_for("index"))

    return render_template("add_recipe.html")


@app.route("/recipe/<int:recipe_id>")
def recipe_detail(recipe_id):
    conn = get_db_connection()
    recipe = conn.execute(
        "SELECT * FROM recipes WHERE id = ?",
        (recipe_id,)
    ).fetchone()
    conn.close()

    if recipe is None:
        flash("Recipe not found.")
        return redirect(url_for("index"))

    return render_template("recipe_detail.html", recipe=recipe)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
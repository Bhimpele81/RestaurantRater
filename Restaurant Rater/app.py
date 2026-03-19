import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "restaurant_rater.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def init_db():
    conn = get_db_connection()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS restaurants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        description TEXT,
        dishes_tried TEXT,
        attendees TEXT,
        visit_date TEXT,
        rating REAL,
        image_filename TEXT
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        rating INTEGER NOT NULL,
        image_filename TEXT
    )
    """)
    conn.commit()
    conn.close()


init_db()


@app.route("/")
def index():
    conn = get_db_connection()
    restaurants = conn.execute("SELECT * FROM restaurants").fetchall()
    recipes = conn.execute("SELECT * FROM recipes").fetchall()
    conn.close()
    return render_template("index.html", restaurants=restaurants, recipes=recipes, highlight=None)


@app.route("/restaurants")
def restaurants_list():
    conn = get_db_connection()
    restaurants = conn.execute("SELECT * FROM restaurants ORDER BY name").fetchall()
    conn.close()
    return render_template("index.html", restaurants=restaurants, recipes=[], highlight=None)


@app.route("/recipes")
def recipes_list():
    conn = get_db_connection()
    recipes = conn.execute("SELECT * FROM recipes ORDER BY name").fetchall()
    conn.close()
    return render_template("index.html", restaurants=[], recipes=recipes, highlight=None)


@app.route("/add_restaurant", methods=["GET", "POST"])
def add_restaurant():
    if request.method == "POST":
        name = request.form["name"]
        category = request.form["category"]
        description = request.form["description"]
        dishes_tried = request.form["dishes_tried"]
        attendees = request.form["attendees"]
        visit_date = request.form["visit_date"]
        rating = float(request.form["rating"])

        file = request.files.get("image")
        filename = None
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO restaurants (name, category, description, dishes_tried, attendees, visit_date, rating, image_filename) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (name, category, description, dishes_tried, attendees, visit_date, rating, filename)
        )
        conn.commit()
        conn.close()

        flash("Restaurant added successfully!")
        return redirect(url_for("index"))

    return render_template("add_restaurant.html", cuisines=["American", "Mexican", "Italian", "Indian", "Chinese", "Other"])


@app.route("/restaurant/<int:restaurant_id>")
def restaurant_detail(restaurant_id):
    conn = get_db_connection()
    restaurant = conn.execute("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,)).fetchone()
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
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO recipes (name, description, rating, image_filename) VALUES (?, ?, ?, ?)",
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
    recipe = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    conn.close()
    if recipe is None:
        flash("Recipe not found.")
        return redirect(url_for("index"))
    return render_template("recipe_detail.html", recipe=recipe)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

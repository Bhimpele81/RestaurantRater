import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.secret_key = "secret"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "restaurant_rater.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file):
    if not file or not file.filename:
        return None

    if not allowed_file(file.filename):
        return None

    original_name = file.filename
    safe_name = "".join(c for c in original_name if c.isalnum() or c in "._-").strip("._")
    if not safe_name:
        safe_name = "upload.jpg"

    final_name = safe_name
    file_path = os.path.join(UPLOAD_FOLDER, final_name)

    counter = 1
    while os.path.exists(file_path):
        if "." in safe_name:
            name_part, ext = safe_name.rsplit(".", 1)
            final_name = f"{name_part}_{counter}.{ext}"
        else:
            final_name = f"{safe_name}_{counter}"
        file_path = os.path.join(UPLOAD_FOLDER, final_name)
        counter += 1

    file.save(file_path)
    return final_name


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
        name TEXT,
        description TEXT,
        rating REAL
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS recipe_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        FOREIGN KEY (recipe_id) REFERENCES recipes (id)
    )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = get_db_connection()

    restaurants = conn.execute(
        "SELECT * FROM restaurants ORDER BY id DESC"
    ).fetchall()

    recipes = conn.execute(
        """
        SELECT
            recipes.id,
            recipes.name,
            recipes.description,
            recipes.rating,
            (
                SELECT filename
                FROM recipe_photos
                WHERE recipe_photos.recipe_id = recipes.id
                ORDER BY id ASC
                LIMIT 1
            ) AS cover_photo
        FROM recipes
        ORDER BY recipes.id DESC
        """
    ).fetchall()

    conn.close()

    return render_template("index.html", restaurants=restaurants, recipes=recipes)


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

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO restaurants
            (name, category, description, dishes_tried, attendees, visit_date, rating)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, category, description, dishes_tried, attendees, visit_date, rating)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    return render_template(
        "add_restaurant.html",
        cuisines=["American", "Mexican", "Italian", "Indian", "Chinese", "Other"]
    )


@app.route("/restaurant/<int:id>")
def restaurant_detail(id):
    conn = get_db_connection()
    restaurant = conn.execute(
        "SELECT * FROM restaurants WHERE id = ?",
        (id,)
    ).fetchone()
    conn.close()

    return render_template("restaurant_detail.html", restaurant=restaurant)


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        rating = float(request.form["rating"])

        conn = get_db_connection()
        cursor = conn.execute(
            "INSERT INTO recipes (name, description, rating) VALUES (?, ?, ?)",
            (name, description, rating)
        )
        recipe_id = cursor.lastrowid

        files = request.files.getlist("images")
        for file in files:
            filename = save_uploaded_file(file)
            if filename:
                conn.execute(
                    "INSERT INTO recipe_photos (recipe_id, filename) VALUES (?, ?)",
                    (recipe_id, filename)
                )

        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    return render_template("add_recipe.html")


@app.route("/recipe/<int:id>")
def recipe_detail(id):
    conn = get_db_connection()

    recipe = conn.execute(
        "SELECT * FROM recipes WHERE id = ?",
        (id,)
    ).fetchone()

    photos = conn.execute(
        "SELECT * FROM recipe_photos WHERE recipe_id = ? ORDER BY id ASC",
        (id,)
    ).fetchall()

    conn.close()

    return render_template("recipe_detail.html", recipe=recipe, photos=photos)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.secret_key = "secret"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "restaurant_rater.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file):
    if not file or not file.filename:
        return None

    if not allowed_file(file.filename):
        return None

    original_name = file.filename
    safe_name = "".join(c for c in original_name if c.isalnum() or c in "._-").strip("._")
    if not safe_name:
        safe_name = "upload.jpg"

    final_name = safe_name
    file_path = os.path.join(UPLOAD_FOLDER, final_name)

    counter = 1
    while os.path.exists(file_path):
        name_part, dot, ext = final_name.rpartition(".")
        if dot == "":
            name_part = final_name
            ext = ""
        final_name = f"{name_part}_{counter}"
        if ext:
            final_name = f"{final_name}.{ext}"
        file_path = os.path.join(UPLOAD_FOLDER, final_name)
        counter += 1

    file.save(file_path)
    return final_name


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
        name TEXT,
        description TEXT,
        rating REAL
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS recipe_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        FOREIGN KEY (recipe_id) REFERENCES recipes (id)
    )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = get_db_connection()

    restaurants = conn.execute(
        "SELECT * FROM restaurants ORDER BY id DESC"
    ).fetchall()

    recipes = conn.execute(
        """
        SELECT
            recipes.id,
            recipes.name,
            recipes.description,
            recipes.rating,
            (
                SELECT filename
                FROM recipe_photos
                WHERE recipe_photos.recipe_id = recipes.id
                ORDER BY id ASC
                LIMIT 1
            ) AS cover_photo
        FROM recipes
        ORDER BY recipes.id DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "index.html",
        restaurants=restaurants,
        recipes=recipes
    )


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

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO restaurants
            (name, category, description, dishes_tried, attendees, visit_date, rating)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, category, description, dishes_tried, attendees, visit_date, rating)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    return render_template(
        "add_restaurant.html",
        cuisines=["American", "Mexican", "Italian", "Indian", "Chinese", "Other"]
    )


@app.route("/restaurant/<int:id>")
def restaurant_detail(id):
    conn = get_db_connection()
    restaurant = conn.execute(
        "SELECT * FROM restaurants WHERE id = ?",
        (id,)
    ).fetchone()
    conn.close()

    return render_template("restaurant_detail.html", restaurant=restaurant)


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        rating = float(request.form["rating"])

        conn = get_db_connection()
        cursor = conn.execute(
            "INSERT INTO recipes (name, description, rating) VALUES (?, ?, ?)",
            (name, description, rating)
        )
        recipe_id = cursor.lastrowid

        files = request.files.getlist("images")
        for file in files:
            filename = save_uploaded_file(file)
            if filename:
                conn.execute(
                    "INSERT INTO recipe_photos (recipe_id, filename) VALUES (?, ?)",
                    (recipe_id, filename)
                )

        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    return render_template("add_recipe.html")


@app.route("/recipe/<int:id>")
def recipe_detail(id):
    conn = get_db_connection()

    recipe = conn.execute(
        "SELECT * FROM recipes WHERE id = ?",
        (id,)
    ).fetchone()

    photos = conn.execute(
        "SELECT * FROM recipe_photos WHERE recipe_id = ? ORDER BY id ASC",
        (id,)
    ).fetchall()

    conn.close()

    return render_template(
        "recipe_detail.html",
        recipe=recipe,
        photos=photos
    )


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.secret_key = "secret"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "restaurant_rater.db")


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


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
        name TEXT,
        description TEXT,
        rating REAL
    )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = get_db_connection()
    restaurants = conn.execute(
        "SELECT * FROM restaurants ORDER BY id DESC"
    ).fetchall()
    recipes = conn.execute(
        "SELECT * FROM recipes ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return render_template(
        "index.html",
        restaurants=restaurants,
        recipes=recipes
    )


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

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO restaurants
            (name, category, description, dishes_tried, attendees, visit_date, rating)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, category, description, dishes_tried, attendees, visit_date, rating)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    return render_template(
        "add_restaurant.html",
        cuisines=["American", "Mexican", "Italian", "Indian", "Chinese", "Other"]
    )


@app.route("/restaurant/<int:id>")
def restaurant_detail(id):
    conn = get_db_connection()
    restaurant = conn.execute(
        "SELECT * FROM restaurants WHERE id = ?",
        (id,)
    ).fetchone()
    conn.close()

    return render_template("restaurant_detail.html", restaurant=restaurant)


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        rating = float(request.form["rating"])

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO recipes (name, description, rating) VALUES (?, ?, ?)",
            (name, description, rating)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    return render_template("add_recipe.html")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
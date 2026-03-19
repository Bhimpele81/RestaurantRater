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

    recent_highlights = []

    for recipe in recipes[:6]:
        if recipe["cover_photo"]:
            recent_highlights.append(
                {
                    "type": "recipe",
                    "id": recipe["id"],
                    "name": recipe["name"],
                    "rating": recipe["rating"],
                    "description": recipe["description"],
                    "image_filename": recipe["cover_photo"],
                }
            )

    for restaurant in restaurants[:6]:
        if restaurant["image_filename"]:
            recent_highlights.append(
                {
                    "type": "restaurant",
                    "id": restaurant["id"],
                    "name": restaurant["name"],
                    "rating": restaurant["rating"],
                    "description": restaurant["description"],
                    "image_filename": restaurant["image_filename"],
                }
            )

    recent_highlights = recent_highlights[:3]

    conn.close()

    return render_template(
        "index.html",
        restaurants=restaurants,
        recipes=recipes,
        recent_highlights=recent_highlights
    )


@app.route("/restaurants")
def restaurants_list():
    q = request.args.get("q", "").strip()

    conn = get_db_connection()

    if q:
        restaurants = conn.execute(
            """
            SELECT * FROM restaurants
            WHERE name LIKE ?
               OR category LIKE ?
               OR description LIKE ?
               OR dishes_tried LIKE ?
               OR attendees LIKE ?
               OR visit_date LIKE ?
            ORDER BY id DESC
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
        restaurants = conn.execute(
            "SELECT * FROM restaurants ORDER BY id DESC"
        ).fetchall()

    conn.close()

    return render_template("restaurants.html", restaurants=restaurants, q=q)


@app.route("/recipes")
def recipes_list():
    q = request.args.get("q", "").strip()

    conn = get_db_connection()

    if q:
        recipes = conn.execute(
            "SELECT * FROM recipes WHERE name LIKE ? OR description LIKE ? ORDER BY id DESC",
            (f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
        recipes = conn.execute(
            "SELECT * FROM recipes ORDER BY id DESC"
        ).fetchall()

    conn.close()

    return render_template("recipes.html", recipes=recipes, q=q)


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

        image_filename = None
        image = request.files.get("image")
        if image and image.filename:
            image_filename = save_uploaded_file(image)

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO restaurants
            (name, category, description, dishes_tried, attendees, visit_date, rating, image_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, category, description, dishes_tried, attendees, visit_date, rating, image_filename)
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

        return redirect(url_for("recipe_detail", id=recipe_id))

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
    app.run(host="0.0.0.0", port=5000, debug=True)
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

    recent_highlights = []

    for recipe in recipes[:6]:
        if recipe["cover_photo"]:
            recent_highlights.append(
                {
                    "type": "recipe",
                    "id": recipe["id"],
                    "name": recipe["name"],
                    "rating": recipe["rating"],
                    "description": recipe["description"],
                    "image_filename": recipe["cover_photo"],
                }
            )

    for restaurant in restaurants[:6]:
        if restaurant["image_filename"]:
            recent_highlights.append(
                {
                    "type": "restaurant",
                    "id": restaurant["id"],
                    "name": restaurant["name"],
                    "rating": restaurant["rating"],
                    "description": restaurant["description"],
                    "image_filename": restaurant["image_filename"],
                }
            )

    recent_highlights = recent_highlights[:3]

    conn.close()

    return render_template(
        "index.html",
        restaurants=restaurants,
        recipes=recipes,
        recent_highlights=recent_highlights
    )


@app.route("/restaurants")
def restaurants_list():
    q = request.args.get("q", "").strip()

    conn = get_db_connection()

    if q:
        restaurants = conn.execute(
            """
            SELECT * FROM restaurants
            WHERE name LIKE ?
               OR category LIKE ?
               OR description LIKE ?
               OR dishes_tried LIKE ?
               OR attendees LIKE ?
               OR visit_date LIKE ?
            ORDER BY id DESC
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
        restaurants = conn.execute(
            "SELECT * FROM restaurants ORDER BY id DESC"
        ).fetchall()

    conn.close()

    return render_template("restaurants.html", restaurants=restaurants, q=q)


@app.route("/recipes")
def recipes_list():
    q = request.args.get("q", "").strip()

    conn = get_db_connection()

    if q:
        recipes = conn.execute(
            """
            SELECT * FROM recipes
            WHERE name LIKE ?
               OR description LIKE ?
            ORDER BY id DESC
            """,
            (f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
        recipes = conn.execute(
            "SELECT * FROM recipes ORDER BY id DESC"
        ).fetchall()

    conn.close()

    return render_template("recipes.html", recipes=recipes, q=q)


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

        image_filename = None
        image = request.files.get("image")
        if image and image.filename:
            image_filename = save_uploaded_file(image)

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO restaurants
            (name, category, description, dishes_tried, attendees, visit_date, rating, image_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, category, description, dishes_tried, attendees, visit_date, rating, image_filename)
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

        return redirect(url_for("recipe_detail", id=recipe_id))

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

    recent_highlights = []

    for recipe in recipes[:6]:
        if recipe["cover_photo"]:
            recent_highlights.append(
                {
                    "type": "recipe",
                    "id": recipe["id"],
                    "name": recipe["name"],
                    "rating": recipe["rating"],
                    "description": recipe["description"],
                    "image_filename": recipe["cover_photo"],
                }
            )

    for restaurant in restaurants[:6]:
        if restaurant["image_filename"]:
            recent_highlights.append(
                {
                    "type": "restaurant",
                    "id": restaurant["id"],
                    "name": restaurant["name"],
                    "rating": restaurant["rating"],
                    "description": restaurant["description"],
                    "image_filename": restaurant["image_filename"],
                }
            )

    recent_highlights = recent_highlights[:3]

    conn.close()

    return render_template(
        "index.html",
        restaurants=restaurants,
        recipes=recipes,
        recent_highlights=recent_highlights
    )


@app.route("/restaurants")
def restaurants_list():
    q = request.args.get("q", "").strip()

    conn = get_db_connection()

    if q:
        restaurants = conn.execute(
            """
            SELECT * FROM restaurants
            WHERE name LIKE ?
               OR category LIKE ?
               OR description LIKE ?
               OR dishes_tried LIKE ?
               OR attendees LIKE ?
               OR visit_date LIKE ?
            ORDER BY id DESC
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
        restaurants = conn.execute(
            "SELECT * FROM restaurants ORDER BY id DESC"
        ).fetchall()

    conn.close()

    return render_template("restaurants.html", restaurants=restaurants, q=q)


@app.route("/recipes")
def recipes_list():
    q = request.args.get("q", "").strip()

    conn = get_db_connection()

    if q:
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
            WHERE recipes.name LIKE ?
               OR recipes.description LIKE ?
            ORDER BY recipes.id DESC
            """,
            (f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
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

    return render_template("recipes.html", recipes=recipes, q=q)


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

        image_filename = None
        image = request.files.get("image")
        if image and image.filename:
            image_filename = save_uploaded_file(image)

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO restaurants
            (name, category, description, dishes_tried, attendees, visit_date, rating, image_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, category, description, dishes_tried, attendees, visit_date, rating, image_filename)
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

        return redirect(url_for("recipe_detail", id=recipe_id))

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

    recent_highlights = []

    for recipe in recipes[:6]:
        if recipe["cover_photo"]:
            recent_highlights.append(
                {
                    "type": "recipe",
                    "id": recipe["id"],
                    "name": recipe["name"],
                    "rating": recipe["rating"],
                    "description": recipe["description"],
                    "image_filename": recipe["cover_photo"],
                }
            )

    for restaurant in restaurants[:6]:
        if restaurant["image_filename"]:
            recent_highlights.append(
                {
                    "type": "restaurant",
                    "id": restaurant["id"],
                    "name": restaurant["name"],
                    "rating": restaurant["rating"],
                    "description": restaurant["description"],
                    "image_filename": restaurant["image_filename"],
                }
            )

    recent_highlights = recent_highlights[:3]

    conn.close()

    return render_template(
        "index.html",
        restaurants=restaurants,
        recipes=recipes,
        recent_highlights=recent_highlights
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

        image_filename = None
        image = request.files.get("image")
        if image and image.filename:
            image_filename = save_uploaded_file(image)

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO restaurants
            (name, category, description, dishes_tried, attendees, visit_date, rating, image_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, category, description, dishes_tried, attendees, visit_date, rating, image_filename)
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

        return redirect(url_for("recipe_detail", id=recipe_id))

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

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.secret_key = "secret"

DATABASE = os.path.join(BASE_DIR, "restaurant_rater.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


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

    return render_template("index.html", restaurants=restaurants, recipes=recipes)


# 🔥 RESTAURANTS PAGE
@app.route("/restaurants")
def restaurants_list():
    q = request.args.get("q", "")

    conn = get_db_connection()

    if q:
        restaurants = conn.execute(
            """
            SELECT * FROM restaurants
            WHERE name LIKE ?
               OR category LIKE ?
               OR description LIKE ?
            ORDER BY id DESC
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
        restaurants = conn.execute(
            "SELECT * FROM restaurants ORDER BY id DESC"
        ).fetchall()

    conn.close()

    return render_template("restaurants.html", restaurants=restaurants, q=q)


# 🔥 RECIPES PAGE
@app.route("/recipes")
def recipes_list():
    q = request.args.get("q", "")

    conn = get_db_connection()

    if q:
        recipes = conn.execute(
            """
            SELECT * FROM recipes
            WHERE name LIKE ?
               OR description LIKE ?
            ORDER BY id DESC
            """,
            (f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
        recipes = conn.execute(
            "SELECT * FROM recipes ORDER BY id DESC"
        ).fetchall()

    conn.close()

    return render_template("recipes.html", recipes=recipes, q=q)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
from flask import Flask, render_template, request, redirect, url_for

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.secret_key = "secret"

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

    restaurant_rows = conn.execute(
        "SELECT * FROM restaurants ORDER BY id DESC"
    ).fetchall()

    recipe_rows = conn.execute(
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

    recent_highlights = []

    for recipe in recipe_rows[:6]:
        if recipe["cover_photo"]:
            recent_highlights.append(
                {
                    "type": "recipe",
                    "id": recipe["id"],
                    "name": recipe["name"],
                    "rating": recipe["rating"],
                    "description": recipe["description"],
                    "image_filename": recipe["cover_photo"],
                }
            )

    for restaurant in restaurant_rows[:6]:
        if restaurant["image_filename"]:
            recent_highlights.append(
                {
                    "type": "restaurant",
                    "id": restaurant["id"],
                    "name": restaurant["name"],
                    "rating": restaurant["rating"],
                    "description": restaurant["description"],
                    "image_filename": restaurant["image_filename"],
                }
            )

    recent_highlights = recent_highlights[:3]

    conn.close()

    return render_template(
        "index.html",
        restaurants=restaurant_rows,
        recipes=recipe_rows,
        recent_highlights=recent_highlights
    )


@app.route("/restaurants")
def restaurants_list():
    q = request.args.get("q", "").strip()

    conn = get_db_connection()

    if q:
        restaurant_rows = conn.execute(
            """
            SELECT * FROM restaurants
            WHERE name LIKE ?
               OR category LIKE ?
               OR description LIKE ?
               OR dishes_tried LIKE ?
               OR attendees LIKE ?
               OR visit_date LIKE ?
            ORDER BY id DESC
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
        restaurant_rows = conn.execute(
            "SELECT * FROM restaurants ORDER BY id DESC"
        ).fetchall()

    conn.close()

    return render_template(
        "restaurants.html",
        restaurants=restaurant_rows,
        q=q
    )


@app.route("/recipes")
def recipes_list():
    q = request.args.get("q", "").strip()

    conn = get_db_connection()

    if q:
        recipe_rows = conn.execute(
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
            WHERE recipes.name LIKE ?
               OR recipes.description LIKE ?
            ORDER BY recipes.id DESC
            """,
            (f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
        recipe_rows = conn.execute(
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
        "recipes.html",
        recipes=recipe_rows,
        q=q
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

        image_filename = None
        image = request.files.get("image")
        if image and image.filename:
            image_filename = save_uploaded_file(image)

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO restaurants
            (name, category, description, dishes_tried, attendees, visit_date, rating, image_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, category, description, dishes_tried, attendees, visit_date, rating, image_filename)
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

        return redirect(url_for("recipe_detail", id=recipe_id))

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
    app.run(host="0.0.0.0", port=5000, debug=True)
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

    recent_highlights = []

    for recipe in recipes[:6]:
        if recipe["cover_photo"]:
            recent_highlights.append(
                {
                    "type": "recipe",
                    "id": recipe["id"],
                    "name": recipe["name"],
                    "rating": recipe["rating"],
                    "description": recipe["description"],
                    "image_filename": recipe["cover_photo"],
                }
            )

    for restaurant in restaurants[:6]:
        if restaurant["image_filename"]:
            recent_highlights.append(
                {
                    "type": "restaurant",
                    "id": restaurant["id"],
                    "name": restaurant["name"],
                    "rating": restaurant["rating"],
                    "description": restaurant["description"],
                    "image_filename": restaurant["image_filename"],
                }
            )

    recent_highlights = recent_highlights[:3]

    conn.close()

    return render_template(
        "index.html",
        restaurants=restaurants,
        recipes=recipes,
        recent_highlights=recent_highlights
    )


@app.route("/restaurants")
def restaurants():
    q = request.args.get("q", "").strip()

    conn = get_db_connection()

    if q:
        restaurants = conn.execute(
            """
            SELECT * FROM restaurants
            WHERE name LIKE ?
               OR category LIKE ?
               OR description LIKE ?
               OR dishes_tried LIKE ?
               OR attendees LIKE ?
               OR visit_date LIKE ?
            ORDER BY id DESC
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
        restaurants = conn.execute(
            "SELECT * FROM restaurants ORDER BY id DESC"
        ).fetchall()

    conn.close()

    return render_template("restaurants.html", restaurants=restaurants, q=q)


@app.route("/recipes")
def recipes_list():
    q = request.args.get("q", "").strip()

    conn = get_db_connection()

    if q:
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
            WHERE recipes.name LIKE ?
               OR recipes.description LIKE ?
            ORDER BY recipes.id DESC
            """,
            (f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
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

    return render_template("recipes.html", recipes=recipes, q=q)


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

        image_filename = None
        image = request.files.get("image")
        if image and image.filename:
            image_filename = save_uploaded_file(image)

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO restaurants
            (name, category, description, dishes_tried, attendees, visit_date, rating, image_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, category, description, dishes_tried, attendees, visit_date, rating, image_filename)
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

        return redirect(url_for("recipe_detail", id=recipe_id))

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

    recent_highlights = []

    for recipe in recipes[:6]:
        if recipe["cover_photo"]:
            recent_highlights.append(
                {
                    "type": "recipe",
                    "id": recipe["id"],
                    "name": recipe["name"],
                    "rating": recipe["rating"],
                    "description": recipe["description"],
                    "image_filename": recipe["cover_photo"],
                }
            )

    for restaurant in restaurants[:6]:
        if restaurant["image_filename"]:
            recent_highlights.append(
                {
                    "type": "restaurant",
                    "id": restaurant["id"],
                    "name": restaurant["name"],
                    "rating": restaurant["rating"],
                    "description": restaurant["description"],
                    "image_filename": restaurant["image_filename"],
                }
            )

    recent_highlights = recent_highlights[:3]

    conn.close()

    return render_template(
        "index.html",
        restaurants=restaurants,
        recipes=recipes,
        recent_highlights=recent_highlights
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

        image_filename = None
        image = request.files.get("image")
        if image and image.filename:
            image_filename = save_uploaded_file(image)

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO restaurants
            (name, category, description, dishes_tried, attendees, visit_date, rating, image_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, category, description, dishes_tried, attendees, visit_date, rating, image_filename)
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

        return redirect(url_for("recipe_detail", id=recipe_id))

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
    app.run(host="0.0.0.0", port=5000, debug=True)
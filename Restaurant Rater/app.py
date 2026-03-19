import os
import sqlite3
import json
import urllib.parse
import urllib.request
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


def delete_uploaded_file(filename):
    if not filename:
        return

    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass


def ensure_column(conn, table_name, column_name, column_definition):
    columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing_column_names = [column["name"] for column in columns]

    if column_name not in existing_column_names:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def geocode_city_state(city, state):
    if not city or not state:
        return None, None

    query = f"{city}, {state}, USA"
    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "limit": 1
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "DinnerRater/1.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            return lat, lon
    except Exception:
        pass

    return None, None


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
        image_filename TEXT,
        city TEXT,
        state TEXT,
        latitude REAL,
        longitude REAL
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

    ensure_column(conn, "restaurants", "name", "TEXT")
    ensure_column(conn, "restaurants", "category", "TEXT")
    ensure_column(conn, "restaurants", "description", "TEXT")
    ensure_column(conn, "restaurants", "dishes_tried", "TEXT")
    ensure_column(conn, "restaurants", "attendees", "TEXT")
    ensure_column(conn, "restaurants", "visit_date", "TEXT")
    ensure_column(conn, "restaurants", "rating", "REAL")
    ensure_column(conn, "restaurants", "image_filename", "TEXT")
    ensure_column(conn, "restaurants", "city", "TEXT")
    ensure_column(conn, "restaurants", "state", "TEXT")
    ensure_column(conn, "restaurants", "latitude", "REAL")
    ensure_column(conn, "restaurants", "longitude", "REAL")

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

    map_restaurants = []
    for restaurant in restaurants:
        if restaurant["latitude"] is not None and restaurant["longitude"] is not None:
            map_restaurants.append({
                "id": restaurant["id"],
                "name": restaurant["name"],
                "city": restaurant["city"] or "",
                "state": restaurant["state"] or "",
                "latitude": restaurant["latitude"],
                "longitude": restaurant["longitude"]
            })

    conn.close()

    return render_template(
        "index.html",
        restaurants=restaurants,
        recipes=recipes,
        recent_highlights=recent_highlights,
        map_restaurants=map_restaurants
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
               OR city LIKE ?
               OR state LIKE ?
            ORDER BY id DESC
            """,
            (
                f"%{q}%",
                f"%{q}%",
                f"%{q}%",
                f"%{q}%",
                f"%{q}%",
                f"%{q}%",
                f"%{q}%",
                f"%{q}%"
            )
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
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        dishes_tried = request.form.get("dishes_tried", "").strip()
        attendees = request.form.get("attendees", "").strip()
        visit_date = request.form.get("visit_date", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()

        rating_value = request.form.get("rating", "").strip()
        rating = float(rating_value) if rating_value else None

        latitude, longitude = geocode_city_state(city, state)

        image_filename = None
        image = request.files.get("image")
        if image and image.filename:
            image_filename = save_uploaded_file(image)

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO restaurants
            (name, category, description, dishes_tried, attendees, visit_date, rating, image_filename, city, state, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                category,
                description,
                dishes_tried,
                attendees,
                visit_date,
                rating,
                image_filename,
                city,
                state,
                latitude,
                longitude
            )
        )
        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    return render_template(
        "add_restaurant.html",
        cuisines=[
            "American",
            "Barbecue",
            "Breakfast",
            "Burgers",
            "Cajun",
            "Caribbean",
            "Chinese",
            "Comfort Food",
            "Deli",
            "French",
            "German",
            "Greek",
            "Hawaiian",
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
            "Southern",
            "Spanish",
            "Steakhouse",
            "Sushi",
            "Thai",
            "Turkish",
            "Vietnamese",
            "Other"
        ]
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


@app.route("/delete_restaurant/<int:id>", methods=["POST"])
def delete_restaurant(id):
    conn = get_db_connection()

    restaurant = conn.execute(
        "SELECT * FROM restaurants WHERE id = ?",
        (id,)
    ).fetchone()

    if restaurant:
        delete_uploaded_file(restaurant["image_filename"])

        conn.execute(
            "DELETE FROM restaurants WHERE id = ?",
            (id,)
        )
        conn.commit()

    conn.close()
    return redirect(url_for("restaurants_list"))


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        rating_value = request.form.get("rating", "").strip()
        rating = float(rating_value) if rating_value else None

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


@app.route("/delete_recipe/<int:id>", methods=["POST"])
def delete_recipe(id):
    conn = get_db_connection()

    photos = conn.execute(
        "SELECT * FROM recipe_photos WHERE recipe_id = ?",
        (id,)
    ).fetchall()

    for photo in photos:
        delete_uploaded_file(photo["filename"])

    conn.execute(
        "DELETE FROM recipe_photos WHERE recipe_id = ?",
        (id,)
    )
    conn.execute(
        "DELETE FROM recipes WHERE id = ?",
        (id,)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("recipes_list"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True)
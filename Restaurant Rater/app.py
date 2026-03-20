import os
import json
import urllib.parse
import urllib.request
from flask import Flask, render_template, request, redirect, url_for
from replit import db

app = Flask(__name__)
app.secret_key = "secret"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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
    if "next_restaurant_id" not in db:
        db["next_restaurant_id"] = 1

    if "next_recipe_id" not in db:
        db["next_recipe_id"] = 1

    if "restaurants" not in db:
        db["restaurants"] = {}

    if "recipes" not in db:
        db["recipes"] = {}


def get_restaurants():
    restaurants = dict(db.get("restaurants", {}))
    restaurant_list = list(restaurants.values())
    restaurant_list.sort(key=lambda x: x["id"], reverse=True)
    return restaurant_list


def save_restaurants(restaurants_dict):
    db["restaurants"] = restaurants_dict


def get_recipes():
    recipes = dict(db.get("recipes", {}))
    recipe_list = list(recipes.values())
    recipe_list.sort(key=lambda x: x["id"], reverse=True)
    return recipe_list


def save_recipes(recipes_dict):
    db["recipes"] = recipes_dict


def compute_average_food_rating(food_items):
    ratings = []

    for item in food_items:
        item_rating = item.get("item_rating")
        if item_rating is not None:
            ratings.append(float(item_rating))

    if not ratings:
        return None

    return round(sum(ratings) / len(ratings), 1)


def build_restaurant_display_data(restaurant):
    food_items = restaurant.get("food_items", [])
    average_food_rating = compute_average_food_rating(food_items)

    if restaurant.get("rating") is not None:
        effective_rating = restaurant.get("rating")
        rating_source = "manual"
    else:
        effective_rating = average_food_rating
        rating_source = "average"

    restaurant_copy = dict(restaurant)
    restaurant_copy["average_food_rating"] = average_food_rating
    restaurant_copy["effective_rating"] = effective_rating
    restaurant_copy["rating_source"] = rating_source
    return restaurant_copy


@app.route("/")
def index():
    restaurants = [build_restaurant_display_data(r) for r in get_restaurants()]
    recipes = get_recipes()

    recent_highlights = []

    for recipe in recipes[:6]:
        if recipe.get("photo_filenames"):
            recent_highlights.append(
                {
                    "type": "recipe",
                    "id": recipe["id"],
                    "name": recipe["name"],
                    "rating": recipe.get("rating"),
                    "description": recipe.get("description"),
                    "image_filename": recipe["photo_filenames"][0],
                }
            )

    for restaurant in restaurants[:6]:
        if restaurant.get("image_filename"):
            recent_highlights.append(
                {
                    "type": "restaurant",
                    "id": restaurant["id"],
                    "name": restaurant["name"],
                    "rating": restaurant.get("effective_rating"),
                    "description": restaurant.get("description"),
                    "image_filename": restaurant.get("image_filename"),
                }
            )

    recent_highlights = recent_highlights[:3]

    map_restaurants = []
    for restaurant in restaurants:
        if restaurant.get("latitude") is not None and restaurant.get("longitude") is not None:
            map_restaurants.append({
                "id": restaurant["id"],
                "name": restaurant["name"],
                "city": restaurant.get("city", ""),
                "state": restaurant.get("state", ""),
                "latitude": restaurant["latitude"],
                "longitude": restaurant["longitude"]
            })

    return render_template(
        "index.html",
        restaurants=restaurants,
        recipes=recipes,
        recent_highlights=recent_highlights,
        map_restaurants=map_restaurants
    )


@app.route("/restaurants")
def restaurants_list():
    q = request.args.get("q", "").strip().lower()
    restaurants = [build_restaurant_display_data(r) for r in get_restaurants()]

    if q:
        filtered_restaurants = []
        for restaurant in restaurants:
            searchable_text = " ".join([
                restaurant.get("name", ""),
                restaurant.get("category", ""),
                restaurant.get("description", ""),
                restaurant.get("dishes_tried", ""),
                restaurant.get("attendees", ""),
                restaurant.get("visit_date", ""),
                restaurant.get("city", ""),
                restaurant.get("state", "")
            ]).lower()

            food_items = restaurant.get("food_items", [])
            for item in food_items:
                searchable_text += " " + item.get("item_name", "").lower()

            if q in searchable_text:
                filtered_restaurants.append(restaurant)

        restaurants = filtered_restaurants

    return render_template("restaurants.html", restaurants=restaurants, q=q)


@app.route("/recipes")
def recipes_list():
    q = request.args.get("q", "").strip().lower()
    recipes = get_recipes()

    if q:
        filtered_recipes = []
        for recipe in recipes:
            searchable_text = " ".join([
                recipe.get("name", ""),
                recipe.get("description", "")
            ]).lower()

            if q in searchable_text:
                filtered_recipes.append(recipe)

        recipes = filtered_recipes

    return render_template("recipes.html", recipes=recipes, q=q)


@app.route("/add_restaurant", methods=["GET", "POST"])
def add_restaurant():
    if request.method == "POST":
        restaurants = dict(db.get("restaurants", {}))
        restaurant_id = db["next_restaurant_id"]

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

        food_item_names = request.form.getlist("food_item_name[]")
        food_item_ratings = request.form.getlist("food_item_rating[]")

        food_items = []
        next_food_item_id = 1

        for item_name, item_rating in zip(food_item_names, food_item_ratings):
            clean_name = item_name.strip()
            clean_rating = item_rating.strip()

            if clean_name:
                numeric_rating = float(clean_rating) if clean_rating else None
                food_items.append({
                    "id": next_food_item_id,
                    "item_name": clean_name,
                    "item_rating": numeric_rating
                })
                next_food_item_id += 1

        restaurants[str(restaurant_id)] = {
            "id": restaurant_id,
            "name": name,
            "category": category,
            "description": description,
            "dishes_tried": dishes_tried,
            "attendees": attendees,
            "visit_date": visit_date,
            "rating": rating,
            "image_filename": image_filename,
            "city": city,
            "state": state,
            "latitude": latitude,
            "longitude": longitude,
            "food_items": food_items
        }

        db["restaurants"] = restaurants
        db["next_restaurant_id"] = restaurant_id + 1

        return redirect(url_for("restaurant_detail", id=restaurant_id))

    return render_template(
        "add_restaurant.html",
        cuisines=[
            "American", "Barbecue", "Breakfast", "Burgers", "Cajun",
            "Caribbean", "Chinese", "Comfort Food", "Deli", "French",
            "German", "Greek", "Hawaiian", "Indian", "Italian",
            "Japanese", "Korean", "Mediterranean", "Mexican",
            "Middle Eastern", "Pizza", "Seafood", "Soul Food",
            "Southern", "Spanish", "Steakhouse", "Sushi", "Thai",
            "Turkish", "Vietnamese", "Other"
        ]
    )


@app.route("/restaurant/<int:id>")
def restaurant_detail(id):
    restaurants = dict(db.get("restaurants", {}))
    restaurant = restaurants.get(str(id))

    if not restaurant:
        return render_template("restaurant_detail.html", restaurant=None)

    restaurant = build_restaurant_display_data(restaurant)
    return render_template("restaurant_detail.html", restaurant=restaurant)


@app.route("/edit_restaurant/<int:id>", methods=["GET", "POST"])
def edit_restaurant(id):
    restaurants = dict(db.get("restaurants", {}))
    restaurant = restaurants.get(str(id))

    if not restaurant:
        return redirect(url_for("restaurants_list"))

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

        image_filename = restaurant.get("image_filename")
        image = request.files.get("image")
        if image and image.filename:
            new_filename = save_uploaded_file(image)
            if new_filename:
                delete_uploaded_file(restaurant.get("image_filename"))
                image_filename = new_filename

        food_item_names = request.form.getlist("food_item_name[]")
        food_item_ratings = request.form.getlist("food_item_rating[]")

        food_items = []
        next_food_item_id = 1

        for item_name, item_rating in zip(food_item_names, food_item_ratings):
            clean_name = item_name.strip()
            clean_rating = item_rating.strip()

            if clean_name:
                numeric_rating = float(clean_rating) if clean_rating else None
                food_items.append({
                    "id": next_food_item_id,
                    "item_name": clean_name,
                    "item_rating": numeric_rating
                })
                next_food_item_id += 1

        restaurants[str(id)] = {
            "id": id,
            "name": name,
            "category": category,
            "description": description,
            "dishes_tried": dishes_tried,
            "attendees": attendees,
            "visit_date": visit_date,
            "rating": rating,
            "image_filename": image_filename,
            "city": city,
            "state": state,
            "latitude": latitude,
            "longitude": longitude,
            "food_items": food_items
        }

        db["restaurants"] = restaurants
        return redirect(url_for("restaurant_detail", id=id))

    restaurant = build_restaurant_display_data(restaurant)

    return render_template(
        "edit_restaurant.html",
        restaurant=restaurant,
        food_items=restaurant.get("food_items", []),
        cuisines=[
            "American", "Barbecue", "Breakfast", "Burgers", "Cajun",
            "Caribbean", "Chinese", "Comfort Food", "Deli", "French",
            "German", "Greek", "Hawaiian", "Indian", "Italian",
            "Japanese", "Korean", "Mediterranean", "Mexican",
            "Middle Eastern", "Pizza", "Seafood", "Soul Food",
            "Southern", "Spanish", "Steakhouse", "Sushi", "Thai",
            "Turkish", "Vietnamese", "Other"
        ]
    )


@app.route("/delete_restaurant/<int:id>", methods=["POST"])
def delete_restaurant(id):
    restaurants = dict(db.get("restaurants", {}))
    restaurant = restaurants.get(str(id))

    if restaurant:
        delete_uploaded_file(restaurant.get("image_filename"))
        del restaurants[str(id)]
        db["restaurants"] = restaurants

    return redirect(url_for("restaurants_list"))


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        recipes = dict(db.get("recipes", {}))
        recipe_id = db["next_recipe_id"]

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        rating_value = request.form.get("rating", "").strip()
        rating = float(rating_value) if rating_value else None

        files = request.files.getlist("images")
        photo_filenames = []

        for file in files:
            filename = save_uploaded_file(file)
            if filename:
                photo_filenames.append(filename)

        recipes[str(recipe_id)] = {
            "id": recipe_id,
            "name": name,
            "description": description,
            "rating": rating,
            "photo_filenames": photo_filenames
        }

        db["recipes"] = recipes
        db["next_recipe_id"] = recipe_id + 1

        return redirect(url_for("recipe_detail", id=recipe_id))

    return render_template("add_recipe.html")


@app.route("/recipe/<int:id>")
def recipe_detail(id):
    recipes = dict(db.get("recipes", {}))
    recipe = recipes.get(str(id))

    if not recipe:
        return render_template("recipe_detail.html", recipe=None, photos=[])

    photos = [{"filename": filename} for filename in recipe.get("photo_filenames", [])]
    return render_template("recipe_detail.html", recipe=recipe, photos=photos)


@app.route("/edit_recipe/<int:id>", methods=["GET", "POST"])
def edit_recipe(id):
    recipes = dict(db.get("recipes", {}))
    recipe = recipes.get(str(id))

    if not recipe:
        return redirect(url_for("recipes_list"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        rating_value = request.form.get("rating", "").strip()
        rating = float(rating_value) if rating_value else None

        photo_filenames = list(recipe.get("photo_filenames", []))

        files = request.files.getlist("images")
        for file in files:
            filename = save_uploaded_file(file)
            if filename:
                photo_filenames.append(filename)

        recipes[str(id)] = {
            "id": id,
            "name": name,
            "description": description,
            "rating": rating,
            "photo_filenames": photo_filenames
        }

        db["recipes"] = recipes
        return redirect(url_for("recipe_detail", id=id))

    photos = [{"filename": filename} for filename in recipe.get("photo_filenames", [])]
    return render_template("edit_recipe.html", recipe=recipe, photos=photos)


@app.route("/delete_recipe/<int:id>", methods=["POST"])
def delete_recipe(id):
    recipes = dict(db.get("recipes", {}))
    recipe = recipes.get(str(id))

    if recipe:
        for filename in recipe.get("photo_filenames", []):
            delete_uploaded_file(filename)

        del recipes[str(id)]
        db["recipes"] = recipes

    return redirect(url_for("recipes_list"))


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True)
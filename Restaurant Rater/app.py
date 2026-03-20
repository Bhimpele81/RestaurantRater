import os
import json
import base64
import mimetypes
import urllib.parse
import urllib.request
from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Text,
    ForeignKey,
    inspect
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session

app = Flask(__name__)
app.secret_key = "secret"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

database_url = os.environ.get("DATABASE_URL")

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    database_url = "sqlite:///" + os.path.join(BASE_DIR, "restaurant_rater.db")

engine = create_engine(database_url, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))
Base = declarative_base()


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    category = Column(String(255))
    description = Column(Text)
    dishes_tried = Column(Text)
    attendees = Column(Text)
    visit_date = Column(String(50))
    rating = Column(Float)
    image_filename = Column(String(255))
    image_data = Column(Text)
    city = Column(String(255))
    state = Column(String(255))
    latitude = Column(Float)
    longitude = Column(Float)

    food_items = relationship(
        "RestaurantFoodItem",
        back_populates="restaurant",
        cascade="all, delete-orphan",
        order_by="RestaurantFoodItem.id"
    )


class RestaurantFoodItem(Base):
    __tablename__ = "restaurant_food_items"

    id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    item_name = Column(String(255), nullable=False)
    item_rating = Column(Float)

    restaurant = relationship("Restaurant", back_populates="food_items")


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    rating = Column(Float)

    photos = relationship(
        "RecipePhoto",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipePhoto.id"
    )


class RecipePhoto(Base):
    __tablename__ = "recipe_photos"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    image_data = Column(Text)

    recipe = relationship("Recipe", back_populates="photos")


def ensure_column(table_name, column_name, column_type):
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]

    if column_name not in columns:
        with engine.begin() as conn:
            conn.exec_driver_sql(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )


def init_db():
    Base.metadata.create_all(bind=engine)
    ensure_column("restaurants", "image_data", "TEXT")
    ensure_column("recipe_photos", "image_data", "TEXT")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def build_safe_filename(original_name):
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

    return final_name, file_path


def build_data_url(filename, file_bytes):
    mime_type = mimetypes.guess_type(filename)[0]

    if not mime_type:
        extension = filename.rsplit(".", 1)[1].lower() if "." in filename else "jpeg"
        if extension == "jpg":
            extension = "jpeg"
        mime_type = f"image/{extension}"

    encoded = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def save_uploaded_image(file):
    if not file or not file.filename:
        return None, None

    if not allowed_file(file.filename):
        return None, None

    final_name, file_path = build_safe_filename(file.filename)
    file_bytes = file.read()

    if not file_bytes:
        return None, None

    with open(file_path, "wb") as saved_file:
        saved_file.write(file_bytes)

    image_data = build_data_url(final_name, file_bytes)
    return final_name, image_data


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


def compute_average_food_rating(food_items):
    ratings = []

    for item in food_items:
        if item.item_rating is not None:
            ratings.append(float(item.item_rating))

    if not ratings:
        return None

    return round(sum(ratings) / len(ratings), 1)


def add_restaurant_display_fields(restaurant):
    average_food_rating = compute_average_food_rating(restaurant.food_items)

    if restaurant.rating is not None:
        restaurant.effective_rating = restaurant.rating
        restaurant.rating_source = "manual"
    else:
        restaurant.effective_rating = average_food_rating
        restaurant.rating_source = "average"

    restaurant.average_food_rating = average_food_rating
    return restaurant


def add_recipe_cover_photo(recipe):
    recipe.cover_photo = recipe.photos[0].filename if recipe.photos else None
    recipe.cover_photo_data = recipe.photos[0].image_data if recipe.photos else None
    return recipe


@app.route("/")
def index():
    db_session = SessionLocal()

    restaurants = db_session.query(Restaurant).order_by(Restaurant.id.desc()).all()
    restaurants = [add_restaurant_display_fields(r) for r in restaurants]

    recipes = db_session.query(Recipe).order_by(Recipe.id.desc()).all()
    recipes = [add_recipe_cover_photo(r) for r in recipes]

    recent_highlights = []

    for recipe in recipes[:6]:
        if recipe.cover_photo or recipe.cover_photo_data:
            recent_highlights.append(
                {
                    "type": "recipe",
                    "id": recipe.id,
                    "name": recipe.name,
                    "rating": recipe.rating,
                    "description": recipe.description,
                    "image_filename": recipe.cover_photo,
                    "image_data": recipe.cover_photo_data,
                }
            )

    for restaurant in restaurants[:6]:
        if restaurant.image_filename or restaurant.image_data:
            recent_highlights.append(
                {
                    "type": "restaurant",
                    "id": restaurant.id,
                    "name": restaurant.name,
                    "rating": restaurant.effective_rating,
                    "description": restaurant.description,
                    "image_filename": restaurant.image_filename,
                    "image_data": restaurant.image_data,
                }
            )

    recent_highlights = recent_highlights[:3]

    map_restaurants = []
    for restaurant in restaurants:
        if restaurant.latitude is not None and restaurant.longitude is not None:
            map_restaurants.append({
                "id": restaurant.id,
                "name": restaurant.name,
                "city": restaurant.city or "",
                "state": restaurant.state or "",
                "latitude": restaurant.latitude,
                "longitude": restaurant.longitude
            })

    db_session.close()

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
    db_session = SessionLocal()

    restaurants = db_session.query(Restaurant).order_by(Restaurant.id.desc()).all()
    restaurants = [add_restaurant_display_fields(r) for r in restaurants]

    if q:
        filtered = []
        for restaurant in restaurants:
            searchable_text = " ".join([
                restaurant.name or "",
                restaurant.category or "",
                restaurant.description or "",
                restaurant.dishes_tried or "",
                restaurant.attendees or "",
                restaurant.visit_date or "",
                restaurant.city or "",
                restaurant.state or ""
            ]).lower()

            for item in restaurant.food_items:
                searchable_text += " " + (item.item_name or "").lower()

            if q in searchable_text:
                filtered.append(restaurant)

        restaurants = filtered

    db_session.close()
    return render_template("restaurants.html", restaurants=restaurants, q=q)


@app.route("/recipes")
def recipes_list():
    q = request.args.get("q", "").strip().lower()
    db_session = SessionLocal()

    recipes = db_session.query(Recipe).order_by(Recipe.id.desc()).all()
    recipes = [add_recipe_cover_photo(r) for r in recipes]

    if q:
        filtered = []
        for recipe in recipes:
            searchable_text = " ".join([
                recipe.name or "",
                recipe.description or ""
            ]).lower()

            if q in searchable_text:
                filtered.append(recipe)

        recipes = filtered

    db_session.close()
    return render_template("recipes.html", recipes=recipes, q=q)


@app.route("/add_restaurant", methods=["GET", "POST"])
def add_restaurant():
    if request.method == "POST":
        db_session = SessionLocal()

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
        image_data = None
        image = request.files.get("image")
        if image and image.filename:
            image_filename, image_data = save_uploaded_image(image)

        restaurant = Restaurant(
            name=name,
            category=category,
            description=description,
            dishes_tried=dishes_tried,
            attendees=attendees,
            visit_date=visit_date,
            rating=rating,
            image_filename=image_filename,
            image_data=image_data,
            city=city,
            state=state,
            latitude=latitude,
            longitude=longitude
        )

        food_item_names = request.form.getlist("food_item_name[]")
        food_item_ratings = request.form.getlist("food_item_rating[]")

        for item_name, item_rating in zip(food_item_names, food_item_ratings):
            clean_name = item_name.strip()
            clean_rating = item_rating.strip()

            if clean_name:
                restaurant.food_items.append(
                    RestaurantFoodItem(
                        item_name=clean_name,
                        item_rating=float(clean_rating) if clean_rating else None
                    )
                )

        db_session.add(restaurant)
        db_session.commit()
        new_id = restaurant.id
        db_session.close()

        return redirect(url_for("restaurant_detail", id=new_id))

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
    db_session = SessionLocal()
    restaurant = db_session.get(Restaurant, id)

    if not restaurant:
        db_session.close()
        return render_template("restaurant_detail.html", restaurant=None)

    restaurant = add_restaurant_display_fields(restaurant)
    db_session.close()
    return render_template("restaurant_detail.html", restaurant=restaurant)


@app.route("/edit_restaurant/<int:id>", methods=["GET", "POST"])
def edit_restaurant(id):
    db_session = SessionLocal()
    restaurant = db_session.get(Restaurant, id)

    if not restaurant:
        db_session.close()
        return redirect(url_for("restaurants_list"))

    if request.method == "POST":
        restaurant.name = request.form.get("name", "").strip()
        restaurant.category = request.form.get("category", "").strip()
        restaurant.description = request.form.get("description", "").strip()
        restaurant.dishes_tried = request.form.get("dishes_tried", "").strip()
        restaurant.attendees = request.form.get("attendees", "").strip()
        restaurant.visit_date = request.form.get("visit_date", "").strip()
        restaurant.city = request.form.get("city", "").strip()
        restaurant.state = request.form.get("state", "").strip()

        rating_value = request.form.get("rating", "").strip()
        restaurant.rating = float(rating_value) if rating_value else None

        latitude, longitude = geocode_city_state(restaurant.city, restaurant.state)
        restaurant.latitude = latitude
        restaurant.longitude = longitude

        image = request.files.get("image")
        if image and image.filename:
            new_filename, new_image_data = save_uploaded_image(image)
            if new_filename or new_image_data:
                delete_uploaded_file(restaurant.image_filename)
                restaurant.image_filename = new_filename
                restaurant.image_data = new_image_data

        restaurant.food_items.clear()

        food_item_names = request.form.getlist("food_item_name[]")
        food_item_ratings = request.form.getlist("food_item_rating[]")

        for item_name, item_rating in zip(food_item_names, food_item_ratings):
            clean_name = item_name.strip()
            clean_rating = item_rating.strip()

            if clean_name:
                restaurant.food_items.append(
                    RestaurantFoodItem(
                        item_name=clean_name,
                        item_rating=float(clean_rating) if clean_rating else None
                    )
                )

        db_session.commit()
        db_session.close()
        return redirect(url_for("restaurant_detail", id=id))

    restaurant = add_restaurant_display_fields(restaurant)
    food_items = restaurant.food_items
    db_session.close()

    return render_template(
        "edit_restaurant.html",
        restaurant=restaurant,
        food_items=food_items,
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
    db_session = SessionLocal()
    restaurant = db_session.get(Restaurant, id)

    if restaurant:
        delete_uploaded_file(restaurant.image_filename)
        db_session.delete(restaurant)
        db_session.commit()

    db_session.close()
    return redirect(url_for("restaurants_list"))


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        db_session = SessionLocal()

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        rating_value = request.form.get("rating", "").strip()
        rating = float(rating_value) if rating_value else None

        recipe = Recipe(
            name=name,
            description=description,
            rating=rating
        )

        files = request.files.getlist("images")
        for file in files:
            filename, image_data = save_uploaded_image(file)
            if filename or image_data:
                recipe.photos.append(RecipePhoto(filename=filename or "uploaded_image", image_data=image_data))

        db_session.add(recipe)
        db_session.commit()
        new_id = recipe.id
        db_session.close()

        return redirect(url_for("recipe_detail", id=new_id))

    return render_template("add_recipe.html")


@app.route("/recipe/<int:id>")
def recipe_detail(id):
    db_session = SessionLocal()
    recipe = db_session.get(Recipe, id)

    if not recipe:
        db_session.close()
        return render_template("recipe_detail.html", recipe=None, photos=[])

    photos = recipe.photos
    db_session.close()
    return render_template("recipe_detail.html", recipe=recipe, photos=photos)


@app.route("/edit_recipe/<int:id>", methods=["GET", "POST"])
def edit_recipe(id):
    db_session = SessionLocal()
    recipe = db_session.get(Recipe, id)

    if not recipe:
        db_session.close()
        return redirect(url_for("recipes_list"))

    if request.method == "POST":
        recipe.name = request.form.get("name", "").strip()
        recipe.description = request.form.get("description", "").strip()

        rating_value = request.form.get("rating", "").strip()
        recipe.rating = float(rating_value) if rating_value else None

        files = request.files.getlist("images")
        for file in files:
            filename, image_data = save_uploaded_image(file)
            if filename or image_data:
                recipe.photos.append(RecipePhoto(filename=filename or "uploaded_image", image_data=image_data))

        db_session.commit()
        db_session.close()
        return redirect(url_for("recipe_detail", id=id))

    photos = recipe.photos
    db_session.close()
    return render_template("edit_recipe.html", recipe=recipe, photos=photos)


@app.route("/delete_recipe/<int:id>", methods=["POST"])
def delete_recipe(id):
    db_session = SessionLocal()
    recipe = db_session.get(Recipe, id)

    if recipe:
        for photo in recipe.photos:
            delete_uploaded_file(photo.filename)

        db_session.delete(recipe)
        db_session.commit()

    db_session.close()
    return redirect(url_for("recipes_list"))


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
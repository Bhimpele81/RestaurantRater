# Dinner Rater

**Himpele Family Favorites** — A full-stack web application for tracking restaurant experiences, rating dishes, saving recipes, and mapping dining locations.

---

## Features

### Restaurants
- Add, edit, and delete restaurant entries
- Store **city and state** with automatic geocoding (latitude/longitude via OpenStreetMap Nominatim API)
- **Interactive map** on the home page showing all restaurant locations with clickable markers (Leaflet.js)
- Rate **individual food items** (1-10 scale) with dynamic add/remove rows
- **Smart overall rating** — auto-calculates from food item averages, or manually override with your own score
- Track: cuisine category, description, dishes tried, attendees, visit date
- Upload a restaurant photo (PNG, JPG, JPEG, GIF, WebP)

### Recipes
- Add, edit, and delete recipes
- Write ingredients and instructions in a single description field
- Upload **multiple photos** per recipe with a responsive grid display
- Delete individual photos from the edit page
- Rate recipes on a 1-10 scale

### Search
- Search restaurants by name, category, description, dishes tried, attendees, visit date, city, state, and food item names
- Search recipes by name and description
- Case-insensitive partial matching

### Home Page
- Recent highlights with cover photos from both restaurants and recipes
- Full interactive restaurant map with markers and popups linking to detail pages
- Quick access to all restaurants and recipes

### Image Handling
- **Dual storage** — every image saved both as a file on disk and as a Base64 data URL in the database
- Ensures portability and works even if file paths change
- Automatic safe filename sanitization to prevent collisions
- Cascade delete removes associated images when a restaurant or recipe is deleted

### Mobile-Friendly
- Responsive grid layouts for restaurant and recipe cards
- Hamburger menu navigation on mobile
- Mobile-optimized forms and detail pages

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask 3.0 |
| ORM | SQLAlchemy 2.0 |
| Database (Dev) | SQLite |
| Database (Prod) | PostgreSQL (via psycopg) |
| Frontend | HTML, CSS, Jinja2 templates |
| Maps | Leaflet.js + OpenStreetMap tiles |
| Geocoding | Nominatim API |
| Server | Gunicorn |
| Hosting | Replit |

---

## Database Schema

### restaurants
| Column | Type | Description |
|--------|------|-------------|
| name | String | Restaurant name |
| category | String | Cuisine type |
| description | Text | General notes/impressions |
| dishes_tried | Text | Other dishes or quick notes |
| attendees | Text | Who was present |
| visit_date | String | Date of visit |
| rating | Float | Manual overall rating (1-10), optional |
| image_filename | String | Uploaded photo filename |
| image_data | Text | Base64-encoded photo |
| city | String | City name |
| state | String | State abbreviation |
| latitude | Float | Auto-geocoded from city/state |
| longitude | Float | Auto-geocoded from city/state |

### restaurant_food_items
| Column | Type | Description |
|--------|------|-------------|
| restaurant_id | FK | Links to restaurant |
| item_name | String | Dish name |
| item_rating | Float | Individual dish rating (1-10) |

### recipes
| Column | Type | Description |
|--------|------|-------------|
| name | String | Recipe name |
| description | Text | Full recipe text (ingredients + instructions) |
| rating | Float | Recipe rating (1-10) |

### recipe_photos
| Column | Type | Description |
|--------|------|-------------|
| recipe_id | FK | Links to recipe |
| filename | String | Photo filename |
| image_data | Text | Base64-encoded photo |

---

## Installation

```bash
git clone <your-repo-url>
cd Dinner_Rater
pip install -r "Restaurant Rater/requirements.txt"
cd "Restaurant Rater"
python app.py
```

The app runs at `http://localhost:5000`. SQLite database is created automatically on first run.

For production, set the `DATABASE_URL` environment variable to a PostgreSQL connection string.

---

## Deployment

Configured for **Replit** with Gunicorn:
```
gunicorn --bind=0.0.0.0:5000 --reuse-port --chdir="Restaurant Rater" app:app
```

Health check endpoint: `/healthz`

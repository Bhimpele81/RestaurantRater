# Restaurant Rater / Dinner Rater

A family-friendly restaurant and recipe rating app with SQLAlchemy ORM, image uploads, and map integration.

## Architecture

### Frontend
- Flask with Jinja2 templates
- Responsive HTML/CSS
- Image uploads to `/static/uploads/`

### Backend
- Python 3.12 + Flask
- SQLAlchemy ORM with support for both SQLite (development) and PostgreSQL (production)
- Geocoding via OpenStreetMap Nominatim API

### Database Configuration

**Development Environment:**
- Uses SQLite file: `restaurant_rater.db` in the Restaurant Rater folder
- Created automatically on app startup via `init_db()`

**Production Environment:**
- Uses PostgreSQL via `DATABASE_URL` environment variable
- Connection pooling configured for reliability:
  - `pool_size=5` (base connections)
  - `max_overflow=10` (burst capacity)
  - `pool_pre_ping=True` (validates connections before use)
  - `pool_recycle=3600` (recycles stale connections after 1 hour)

## Database Models

- **Restaurant**: Main restaurant entry with name, category, description, rating, image, geocoding
- **RestaurantFoodItem**: Individual dishes tried at a restaurant with ratings
- **Recipe**: Recipe entry with name, description, rating
- **RecipePhoto**: Photos associated with recipes (stored as files + base64 data)

## Key Features

1. **Restaurant Tracking**
   - Store favorite restaurants with ratings and notes
   - Track specific dishes tried with individual ratings
   - Automatic geolocation via city/state

2. **Recipe Management**
   - Save favorite recipes with photos
   - Multiple photo support

3. **Search & Filter**
   - Full-text search across restaurants and recipes

4. **Image Upload**
   - Store photos in `/static/uploads/`
   - Images persist across deployments
   - Support for PNG, JPG, JPEG, GIF, WebP

## Running Locally

Workflow: `Start application`
```
python Restaurant\ Rater/app.py
```
Runs on `http://localhost:5000`

Uses local SQLite database at `Restaurant Rater/restaurant_rater.db`

## Deployment

- **Target**: VM (always running)
- **Production Database**: PostgreSQL (set via `DATABASE_URL` environment variable)
- **Uploads**: Persist in `/static/uploads/` across deployments
- **Data**: Never overwritten when publishing

## Critical Notes

- ✅ Development and Production databases are **completely separate**
- ✅ Production restaurant data is **NOT** affected by development changes
- ✅ Uploaded images persist in production across deployments
- ✅ PostgreSQL connection pooling handles intermittent connection drops gracefully

## Technology Stack

- Flask 3.0+
- SQLAlchemy 2.0+
- psycopg (PostgreSQL driver)
- Werkzeug (file uploads)

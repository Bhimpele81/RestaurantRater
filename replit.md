# Restaurant Rater

A Flask web application for rating and reviewing restaurants, using SQLite for data storage.

## Architecture

- **Backend**: Python 3.12 + Flask
- **Database**: SQLite (file: `Restaurant Rater/restaurants.db`)
- **Templates**: Jinja2 (located in `Restaurant Rater/Templates/`)
- **Static files**: `Restaurant Rater/static/`

## Project Structure

```
Restaurant Rater/
  app.py           # Main Flask application
  Templates/       # Jinja2 HTML templates
    base.html
    index.html
    add_restaurant.html
    restaurant_detail.html
  static/
    style.css
```

## Running the App

The workflow `Start application` runs:
```
cd 'Restaurant Rater' && python app.py
```
on port 5000 (host: 0.0.0.0).

## Features

- List all restaurants with average ratings
- Add new restaurants (name, address, cuisine)
- View restaurant details and all reviews
- Submit star ratings and notes for each restaurant

## Dependencies

- flask
- gunicorn (for production)

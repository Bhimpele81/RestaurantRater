# Dinner Rater

Dinner Rater is a full-stack web application for tracking restaurant experiences and saving favorite recipes in one place.

It helps users:
- rate restaurants and individual food items
- save recipes with photos
- search past meals and recipes
- organize dining memories in a simple, visual way

## Features

### Restaurants
- Add new restaurants
- Store city and state information
- Rate individual food items
- View restaurant details
- Edit and delete restaurant entries
- Search restaurants

### Recipes
- Add recipes with ingredients and instructions
- Upload one or more recipe photos
- View recipe details
- Edit and delete recipes
- Search recipes

### Shared Features
- Image upload support
- Search across content
- Mobile-friendly responsive layout
- PostgreSQL in production
- SQLite in development

## Tech Stack

- **Backend:** Flask
- **Database ORM:** SQLAlchemy
- **Production Database:** PostgreSQL
- **Development Database:** SQLite
- **Frontend:** HTML, CSS, Jinja templates
- **Forms / Routing:** Flask
- **Image Handling:** File upload + stored image references

## Project Goal

The goal of Dinner Rater is to become both:
- a polished **website**
- and an **app-like experience** for mobile users

The current roadmap is:
1. polish the existing Flask website
2. make it fully responsive
3. add Progressive Web App (PWA) support
4. add API endpoints
5. later expand into a native mobile app

## Installation

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd <your-repo-folder>

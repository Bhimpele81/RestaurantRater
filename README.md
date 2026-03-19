# 🍽️ Dinner Rater

A simple web app for tracking and rating restaurants and recipes with your family.

## 📌 Overview

Dinner Rater allows users to:
- Save restaurants they’ve visited
- Rate experiences (1–10 scale)
- Track who attended and what dishes were tried
- Add and rate favorite recipes
- Upload photos for recipes
- View recent highlights with images

This project was built using Flask (Python) and SQLite.

---

## 🚀 Features

### Restaurants
- Add restaurant name, cuisine, and notes
- Record visit date and attendees
- Track dishes tried
- Rate each experience

### Recipes
- Save favorite recipes
- Add notes and ratings
- Upload multiple photos

### Homepage
- View all restaurants and recipes
- “Recent Highlights” section showing recent entries with photos

---

## 🛠️ Tech Stack

- Python (Flask)
- SQLite database
- HTML / CSS
- Jinja templates

---

## 📁 Project Structure

Restaurant Rater/

├── app.py  
├── restaurant_rater.db  

├── templates/  
│   ├── base.html  
│   ├── index.html  
│   ├── add_restaurant.html  
│   ├── add_recipe.html  
│   ├── restaurant_detail.html  
│   └── recipe_detail.html  

├── static/  
│   ├── style.css  
│   └── uploads/  

---

## ▶️ How to Run

1. Install dependencies (if needed):

pip install flask

2. Run the app:

python app.py

3. Open in browser:

http://127.0.0.1:5000

---

## 📸 Future Improvements

- Add restaurant photo uploads  
- User accounts (family members)  
- Search and filtering  
- Edit/delete entries  
- Mobile-friendly improvements  

---

## 🙌 Notes

This project was built as a beginner-friendly way to learn:
- Web development with Flask  
- Working with databases  
- Building a full-stack app from scratch  

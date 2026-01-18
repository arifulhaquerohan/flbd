# FlatLand & Interior Project

A premium web-based project for buying/selling flats and professional interior design services.

## Features
- **Flat Trading**: Post and browse verified flat listings.
- **Interior Design Hub**: A dedicated section for interior designers to showcase portfolios and services.
- **Premium UI**: Modern dark theme with glassmorphism and responsive design.

## Tech Stack
- **Backend**: Python (Flask)
- **Database**: PostgreSQL (Primary) / SQLite (Development)
- **Frontend**: HTML5, CSS3, JS, Bootstrap 5

## Getting Started

### 1. Prerequisites
- Python 3.x
- PostgreSQL (Optional for local testing, SQLite is default)

### 2. Installation
```bash
# Clone the repository (if applicable)
# Navigate to project folder
python3 -m venv venv
source venv/bin/activate  # On Linux/macOS
pip install -r requirements.txt
```

### 3. Database Configuration (PostgreSQL)
1. Create a database in PostgreSQL:
   ```sql
   CREATE DATABASE flatland_db;
   ```
2. Update the `.env` file:
   ```env
   DATABASE_URL=postgresql://your_username:your_password@localhost:5432/flatland_db
   ```
3. The app will automatically create tables on the first run.

### 4. Running the App
```bash
python app.py
```
Open `http://localhost:5000` in your browser.

## Project Structure
- `app.py`: Main application logic and routes.
- `models.py`: Database models for Users, Flats, and Interior Services.
- `templates/`: HTML templates (Jinja2).
- `static/`: CSS, JS, and project images.

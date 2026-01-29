# FlatLand & Interior Project

A premium web-based project for buying/selling flats and professional interior design services.

## Features
- **Flat Trading**: Post and browse verified flat listings.
- **Interior Design Hub**: A dedicated section for interior designers to showcase portfolios and services.
- **Premium UI**: Editorial light theme with glassmorphism, motion, and responsive layouts.

## Tech Stack
- **Backend**: Python (Django)
- **Database**: PostgreSQL (Primary) / SQLite (Development)
- **Frontend**: HTML5, CSS3, JS (Tailwind CDN + Alpine)

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
3. Run migrations:
   ```bash
   python manage.py makemigrations core
   python manage.py migrate
   ```
4. If `ADMIN_EMAIL` and `ADMIN_PASSWORD` are set in `.env`, the first admin user is created automatically on migrate.

### 4. Running the App
```bash
python manage.py runserver
```
Open `http://localhost:8000` in your browser.

### 5. Production (Gunicorn)
```bash
gunicorn -w 2 -b 0.0.0.0:8000 wsgi:application
```
Adjust workers based on CPU cores and traffic (e.g. `-w 4`).

### 6. Admin Access
- Custom admin dashboard lives at `/{ADMIN_PATH}` (set in `.env`).
- Django admin is available at `/django-admin/`.

## Security checklist
- Set `SECRET_KEY` to a long random value in `.env`.
- Use a non-guessable `ADMIN_PATH` and set `ADMIN_EMAIL` / `ADMIN_PASSWORD`.
- In production, set `SESSION_COOKIE_SECURE=1` and serve over HTTPS.

## Project Structure
- `config/`: Django settings, URLs, WSGI/ASGI.
- `core/`: Django app (models, views, utilities).
- `manage.py`: Django management entrypoint.
- `wsgi.py`: WSGI entrypoint for production.
- `app.py` / `models.py`: Legacy Flask files kept for reference.
- `templates/`: HTML templates (Jinja2).
- `static/`: CSS, JS, and project images.

# FlatLand & Interior Project

A Flask-based marketplace for flat listings and interior design services.

## Stack
- Backend: Flask + SQLAlchemy
- Database: PostgreSQL for production, SQLite for local development
- Frontend: Jinja templates, compiled Tailwind CSS, Alpine.js
- Production server: Gunicorn behind Nginx

## Local setup

### 1. Install Python dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Install frontend build dependency
```bash
npm install
```

### 3. Create environment file
```bash
cp .env.example .env
```

Update the values you care about, especially:
- `SECRET_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `ADMIN_PATH`
- `DATABASE_URL` if you want PostgreSQL instead of SQLite

### 4. Build CSS
```bash
npm run build:css
```

For active frontend work:
```bash
npm run watch:css
```

### 5. Run the app
```bash
source venv/bin/activate
python app.py
```

Open `http://127.0.0.1:5001`.

## Local data

By default the app stores:
- SQLite database at `instance/flatland.db`
- Uploaded images at `static/uploads/`

Those are the two folders/files you need to preserve for a full local backup.

## Production setup

### Recommended environment
- Ubuntu or another VPS with persistent disk
- PostgreSQL
- Redis optional but recommended for shared cache/rate limiting
- Nginx in front of Gunicorn

### Environment variables
Important production variables:

```env
SECRET_KEY=replace-me
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/flatland_db
TRUST_PROXY=1
FORCE_HTTPS=1
SESSION_COOKIE_SECURE=1
REDIS_URL=redis://127.0.0.1:6379/0
RATELIMIT_STORAGE_URI=redis://127.0.0.1:6379/1
```

### Build assets
```bash
npm ci
npm run build:css
```

### Run Gunicorn
```bash
source venv/bin/activate
gunicorn -c gunicorn.conf.py wsgi:application
```

You can also use the included `Procfile` on platforms that support it.

### Nginx
An example server block is included at `deploy/nginx-flatland.conf`.

## Performance improvements already applied
- Tailwind is compiled ahead of time instead of loaded from the CDN at runtime
- Public pages already send cache-friendly headers
- Static assets use versioned URLs and long-lived cache headers
- Uploaded images are resized/compressed before saving
- Flat detail and interior detail pages eager-load gallery images
- Admin lists are paginated instead of loading every row at once
- Optional Redis-backed shared cache/rate limiting is supported through env vars

## Restore / migrate

To restore the project on a new server:

1. Copy the codebase
2. Restore `.env`
3. Restore `static/uploads/`
4. Restore either:
   - `instance/flatland.db` for SQLite, or
   - your PostgreSQL database dump
5. Reinstall dependencies
6. Run `npm run build:css`
7. Start Gunicorn

## Useful paths
- App entrypoint: `app.py`
- WSGI entrypoint: `wsgi.py`
- Templates: `templates/`
- Static assets: `static/`
- Uploads: `static/uploads/`
- Local database: `instance/flatland.db`

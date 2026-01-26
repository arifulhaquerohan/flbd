import os
import time
import re
from urllib.parse import urlparse, parse_qs
from flask import Flask, render_template, request, redirect, url_for, flash, abort, Response
from datetime import timedelta, datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models import db, User, Flat, InteriorService, Lead
from sqlalchemy import or_, text
from sqlalchemy.orm import load_only, joinedload

from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
from functools import wraps
from werkzeug.utils import secure_filename

load_dotenv()

def resolve_instance_path():
    explicit = os.getenv('INSTANCE_PATH')
    base_dir = os.path.dirname(os.path.abspath(__file__))
    default_path = os.path.join(base_dir, 'instance')
    if explicit:
        candidate = explicit
    elif os.getenv('VERCEL') or os.getenv('AWS_LAMBDA_FUNCTION_NAME') or os.getenv('AWS_EXECUTION_ENV'):
        candidate = '/tmp/instance'
    else:
        candidate = default_path
    try:
        os.makedirs(candidate, exist_ok=True)
        return candidate
    except OSError:
        fallback = '/tmp/instance'
        try:
            os.makedirs(fallback, exist_ok=True)
            return fallback
        except OSError:
            return default_path

LISTING_STATUSES = {'pending', 'approved', 'rejected'}
LEAD_STATUSES = {'new', 'contacted', 'closed'}

<<<<<<< HEAD
app = Flask(__name__)
=======
<<<<<<< HEAD
instance_path = os.getenv('INSTANCE_PATH')
if not instance_path and (os.getenv('VERCEL') or os.getenv('VERCEL_ENV')):
    # Vercel's filesystem is read-only except /tmp.
    instance_path = '/tmp/instance'

app = Flask(__name__, instance_path=instance_path, instance_relative_config=True) if instance_path else Flask(__name__)
=======
app = Flask(__name__, instance_path=resolve_instance_path())
>>>>>>> 028daaa (major update)
>>>>>>> 2ecb584 ( update)
compress = Compress()
csrf = CSRFProtect()

# Respect upstream proxies when configured (e.g., nginx / load balancer).
if os.getenv('TRUST_PROXY', '0') == '1':
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Brute-force protection
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["2000 per day", "500 per hour"],
    storage_uri="memory://",
)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-7755')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', '0') == '1'
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
app.config['REMEMBER_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', '0') == '1'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=6)
app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024
app.config['COMPRESS_MIN_SIZE'] = int(os.getenv('COMPRESS_MIN_SIZE', '512'))
app.config['COMPRESS_LEVEL'] = int(os.getenv('COMPRESS_LEVEL', '6'))
app.config['COMPRESS_MIMETYPES'] = [
    'text/html',
    'text/css',
    'application/javascript',
    'application/json',
    'application/xml',
    'text/xml',
    'text/plain',
    'image/svg+xml',
]

# Secure Admin Path from .env
ADMIN_PATH = os.getenv('ADMIN_PATH', 'admin')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
ADMIN_PATH = ADMIN_PATH.strip().strip('/')
if not ADMIN_PATH:
    ADMIN_PATH = 'admin'

# Database configuration
database_url = os.getenv('DATABASE_URL', 'sqlite:///flatland.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 280,
}
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000 # Cache static files for 1 year
app.config['LISTINGS_PER_PAGE'] = int(os.getenv('LISTINGS_PER_PAGE', '9'))
app.config['ALLOWED_IMAGE_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'webp'}
app.config['DEFAULT_META_DESCRIPTION'] = (
    'FlatlandBD is a trusted platform for buying and selling flats, plus premium interior design services in Bangladesh.'
)
app.config['DEFAULT_OG_IMAGE'] = os.getenv(
    'DEFAULT_OG_IMAGE',
    'https://images.unsplash.com/photo-1505691938895-1758d7feb511?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=80'
)

<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
>>>>>>> 2ecb584 ( update)
PUBLIC_CACHE_ENDPOINTS = {
    'index',
    'flats',
    'interior',
    'flat_detail',
    'interior_detail',
    'robots',
    'sitemap',
}
PUBLIC_CACHE_TTL = 120
PUBLIC_CACHE_TTL_LONG = 3600

<<<<<<< HEAD
=======
>>>>>>> 028daaa (major update)
>>>>>>> 2ecb584 ( update)
compress.init_app(app)
csrf.init_app(app)
db.init_app(app)

def static_url(filename):
    if not filename:
        return ''
    file_path = os.path.join(app.static_folder, filename)
    version = None
    try:
        version = int(os.path.getmtime(file_path))
    except OSError:
        version = None
    if version:
        return url_for('static', filename=filename, v=version)
    return url_for('static', filename=filename)

app.jinja_env.globals['static_url'] = static_url

@app.context_processor
def inject_meta_defaults():
    return {
        'default_meta_description': app.config['DEFAULT_META_DESCRIPTION'],
        'default_og_image': app.config['DEFAULT_OG_IMAGE'],
    }

def is_allowed_image(filename):
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in app.config['ALLOWED_IMAGE_EXTENSIONS']

def save_uploaded_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    if not is_allowed_image(file_storage.filename):
        return None
    upload_dir = os.path.join(app.static_folder, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    safe_name = secure_filename(file_storage.filename)
    timestamp = int(time.time() * 1000)
    filename = f"{timestamp}_{safe_name}"
    file_storage.save(os.path.join(upload_dir, filename))
    return url_for('static', filename=f'uploads/{filename}')

def coerce_float(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback

def coerce_int(value, fallback=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback

def summarize_text(text, limit=155):
    if not text:
        return None
    compact = ' '.join(str(text).split())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip()

YOUTUBE_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{11}$')

def extract_youtube_id(url):
    if not url:
        return None
    trimmed = str(url).strip()
    if not trimmed:
        return None
    if YOUTUBE_ID_RE.match(trimmed):
        return trimmed
    try:
        parsed = urlparse(trimmed)
    except ValueError:
        return None
    host = (parsed.netloc or '').lower()
    path = parsed.path or ''
    if host in {'youtu.be', 'www.youtu.be'}:
        candidate = path.lstrip('/').split('/')[0]
        return candidate if YOUTUBE_ID_RE.match(candidate) else None
    if host.endswith('youtube.com') or host.endswith('youtube-nocookie.com'):
        if path == '/watch':
            query = parse_qs(parsed.query or '')
            candidate = query.get('v', [''])[0]
            return candidate if YOUTUBE_ID_RE.match(candidate) else None
        parts = [part for part in path.split('/') if part]
        if len(parts) >= 2 and parts[0] in {'embed', 'shorts', 'v'}:
            candidate = parts[1]
            return candidate if YOUTUBE_ID_RE.match(candidate) else None
    return None

def build_youtube_embed(url):
    video_id = extract_youtube_id(url)
    if not video_id:
        return None
    return f"https://www.youtube-nocookie.com/embed/{video_id}?rel=0&modestbranding=1"

def build_youtube_watch(url):
    video_id = extract_youtube_id(url)
    if not video_id:
        return None
    return f"https://youtu.be/{video_id}"

def ensure_schema_updates():
    table_name = Flat.__tablename__
    inspector = db.inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    
    if 'video_url' not in columns:
        try:
            with db.engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN video_url VARCHAR(500)"))
            print("Added video_url column to Flat table.")
        except Exception as e:
            print(f"Error adding column: {e}")

# Login Manager Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = "strong"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

_STATS_CACHE = {}

def get_cached_value(key, ttl_seconds, factory):
    now = time.monotonic()
    cached = _STATS_CACHE.get(key)
    if cached and cached['expires_at'] > now:
        return cached['value']
    value = factory()
    _STATS_CACHE[key] = {'value': value, 'expires_at': now + ttl_seconds}
    return value

def safe_next_path():
    path = request.full_path if request.query_string else request.path
    if not path:
        return '/'
    if path.endswith('?'):
        path = path[:-1]
    if '://' in path or path.startswith('//') or '..' in path:
        return '/'
    if not path.startswith('/'):
        return f'/{path}'
    return path

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=safe_next_path()))
        if current_user.role != 'admin':
            abort(404)
        return f(*args, **kwargs)
    return decorated_function

def require_admin():
    # Legacy function for inline checks
    if not current_user.is_authenticated or current_user.role != 'admin':
        abort(404)

@app.after_request
def add_security_headers(response):
    csp_parts = [
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'self'",
        "form-action 'self'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.tailwindcss.com",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.tailwindcss.com",
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com",
        "img-src 'self' data: https:",
        "frame-src 'self' https://www.google.com https://maps.google.com https://maps.gstatic.com https://www.youtube.com https://www.youtube-nocookie.com",
        "connect-src 'self'",
    ]
    response.headers.setdefault('Content-Security-Policy', '; '.join(csp_parts))
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=(), payment=()')
    if request.is_secure:
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
>>>>>>> 2ecb584 ( update)
    if (
        request.method == 'GET'
        and not current_user.is_authenticated
        and not response.headers.get('Set-Cookie')
        and request.endpoint in PUBLIC_CACHE_ENDPOINTS
    ):
        ttl = PUBLIC_CACHE_TTL_LONG if request.endpoint in {'robots', 'sitemap'} else PUBLIC_CACHE_TTL
        response.headers.setdefault('Cache-Control', f'public, max-age={ttl}, stale-while-revalidate={ttl // 2}')
<<<<<<< HEAD
=======
>>>>>>> 028daaa (major update)
>>>>>>> 2ecb584 ( update)
    vary = response.headers.get('Vary')
    if vary:
        if 'Accept-Encoding' not in vary:
            response.headers['Vary'] = f'{vary}, Accept-Encoding'
    else:
        response.headers['Vary'] = 'Accept-Encoding'
    return response

with app.app_context():
    ensure_schema_updates()

def normalize_preview_path(raw_path):
    if not raw_path:
        return '/'
    path = raw_path.strip()
    if not path:
        return '/'
    if '://' in path or path.startswith('//') or '..' in path:
        return '/'
    if not path.startswith('/'):
        path = f'/{path}'
    if path.startswith('/preview'):
        return '/'
    return path

def get_listing_item(item_type, item_id):
    if item_type == 'flat':
        return Flat.query.get_or_404(item_id)
    if item_type == 'interior':
        return InteriorService.query.get_or_404(item_id)
    abort(404)

def normalize_status(status):
    if not status:
        return None
    status = status.strip().lower()
    if status in LISTING_STATUSES:
        return status
    return None

def normalize_lead_status(status):
    if not status:
        return None
    status = status.strip().lower()
    if status in LEAD_STATUSES:
        return status
    return None

@app.route('/robots.txt')
def robots():
    rules = [
        'User-agent: *',
        f'Disallow: /{ADMIN_PATH}',
        'Disallow: /preview',
        'Disallow: /login',
        'Disallow: /post-listing',
        f'Sitemap: {url_for("sitemap", _external=True)}',
    ]
    return Response('\n'.join(rules), mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap():
    pages = []
    today = datetime.utcnow().date().isoformat()
    static_pages = ['index', 'flats', 'interior', 'login']
    for endpoint in static_pages:
        pages.append({'loc': url_for(endpoint, _external=True), 'lastmod': today})

    flats = Flat.query.filter_by(status='approved').with_entities(Flat.id, Flat.created_at).all()
    for flat_id, created_at in flats:
        lastmod = created_at.date().isoformat() if created_at else today
        pages.append({'loc': url_for('flat_detail', id=flat_id, _external=True), 'lastmod': lastmod})

    services = InteriorService.query.filter_by(status='approved').with_entities(
        InteriorService.id, InteriorService.created_at
    ).all()
    for service_id, created_at in services:
        lastmod = created_at.date().isoformat() if created_at else today
        pages.append({'loc': url_for('interior_detail', id=service_id, _external=True), 'lastmod': lastmod})

    xml = render_template('sitemap.xml', pages=pages)
    return Response(xml, mimetype='application/xml')

@app.route(f'/{ADMIN_PATH}/export/<item_type>')
@admin_required
@limiter.limit("20 per minute")
def export_data(item_type):
    import csv
    from io import StringIO

    status_filter = request.args.get('status', 'all').strip().lower()
    search = request.args.get('q', '').strip()

    output = StringIO()
    writer = csv.writer(output)

    if item_type == 'flats':
        if status_filter not in LISTING_STATUSES:
            status_filter = 'all'
        query = Flat.query.options(joinedload(Flat.owner))
        if status_filter in LISTING_STATUSES:
            query = query.filter_by(status=status_filter)
        if search:
            like = f"%{search}%"
            query = query.filter(or_(Flat.title.ilike(like), Flat.location.ilike(like)))
        writer.writerow([
<<<<<<< HEAD
            'id', 'title', 'location', 'price', 'bhk', 'area_sqft', 'status', 'owner', 'created_at', 'image_url', 'video_url'
=======
<<<<<<< HEAD
            'id', 'title', 'location', 'price', 'bhk', 'area_sqft', 'status', 'owner', 'created_at', 'image_url'
=======
            'id', 'title', 'location', 'price', 'bhk', 'area_sqft', 'status', 'owner', 'created_at', 'image_url', 'video_url'
>>>>>>> 028daaa (major update)
>>>>>>> 2ecb584 ( update)
        ])
        for item in query.order_by(Flat.created_at.desc()).all():
            writer.writerow([
                item.id,
                item.title,
                item.location,
                item.price,
                item.bhk,
                item.area_sqft,
                item.status,
                item.owner.username if item.owner else '',
                item.created_at.isoformat() if item.created_at else '',
                item.image_url or '',
<<<<<<< HEAD
                item.video_url or '',
=======
<<<<<<< HEAD
=======
                item.video_url or '',
>>>>>>> 028daaa (major update)
>>>>>>> 2ecb584 ( update)
            ])
        filename = 'flats.csv'
    elif item_type == 'services':
        if status_filter not in LISTING_STATUSES:
            status_filter = 'all'
        query = InteriorService.query.options(joinedload(InteriorService.provider))
        if status_filter in LISTING_STATUSES:
            query = query.filter_by(status=status_filter)
        if search:
            like = f"%{search}%"
            query = query.filter(InteriorService.provider_name.ilike(like))
        writer.writerow([
            'id', 'provider_name', 'service_type', 'starting_price', 'status', 'provider', 'created_at',
            'image_url', 'portfolio_url'
        ])
        for item in query.order_by(InteriorService.created_at.desc()).all():
            writer.writerow([
                item.id,
                item.provider_name,
                item.service_type,
                item.starting_price,
                item.status,
                item.provider.username if item.provider else '',
                item.created_at.isoformat() if item.created_at else '',
                item.image_url or '',
                item.portfolio_url or '',
            ])
        filename = 'services.csv'
    elif item_type == 'leads':
        if status_filter not in LEAD_STATUSES:
            status_filter = 'all'
        query = Lead.query
        if status_filter in LEAD_STATUSES:
            query = query.filter_by(status=status_filter)
        if search:
            like = f"%{search}%"
            query = query.filter(
                or_(
                    Lead.name.ilike(like),
                    Lead.email.ilike(like),
                    Lead.phone.ilike(like),
                    Lead.message.ilike(like),
                )
            )
        writer.writerow(['id', 'name', 'phone', 'email', 'interest', 'message', 'status', 'created_at'])
        for item in query.order_by(Lead.created_at.desc()).all():
            writer.writerow([
                item.id,
                item.name,
                item.phone or '',
                item.email or '',
                item.interest or '',
                item.message,
                item.status,
                item.created_at.isoformat() if item.created_at else '',
            ])
        filename = 'leads.csv'
    else:
        abort(404)

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

with app.app_context():
    db.create_all()
    # Create admin only if explicitly configured in env
    if not User.query.filter_by(role='admin').first():
        if ADMIN_EMAIL and ADMIN_PASSWORD:
            admin = User(username=ADMIN_USERNAME, email=ADMIN_EMAIL, role='admin')
            admin.set_password(ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.commit()
            print("Admin user created from environment variables.")
        else:
            print("No admin user found. Set ADMIN_EMAIL and ADMIN_PASSWORD in .env to bootstrap one.")

@app.route('/')
def index():
<<<<<<< HEAD
=======
<<<<<<< HEAD
    stats = {
        'flats': Flat.query.filter_by(status='approved').count(),
        'studios': InteriorService.query.filter_by(status='approved').count(),
    }
=======
>>>>>>> 2ecb584 ( update)
    stats = get_cached_value(
        'public_stats',
        60,
        lambda: {
            'flats': Flat.query.filter_by(status='approved').count(),
            'studios': InteriorService.query.filter_by(status='approved').count(),
        },
    )
<<<<<<< HEAD
=======
>>>>>>> 028daaa (major update)
>>>>>>> 2ecb584 ( update)
    return render_template(
        'index.html',
        stats=stats,
        meta_description=app.config['DEFAULT_META_DESCRIPTION'],
        meta_image=app.config['DEFAULT_OG_IMAGE'],
    )

@app.route('/preview')
@admin_required
def preview():
    initial_path = normalize_preview_path(request.args.get('path', '/'))
    preview_pages = [
        {'label': 'Home', 'path': '/'},
        {'label': 'Flats', 'path': '/flats'},
        {'label': 'Interior', 'path': '/interior'},
        {'label': 'Login', 'path': '/login'},
    ]
    return render_template('preview.html', initial_path=initial_path, preview_pages=preview_pages)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter(User.email.ilike(email)).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('index'))
        
        flash('Invalid email or password', 'danger')
    return render_template(
        'login.html',
        meta_description='Admin login for FlatlandBD.',
        meta_type='website',
    )

@app.route('/signup', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def signup():
    abort(404)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/flat/<int:id>')
def flat_detail(id):
    flat = Flat.query.get_or_404(id)
    if flat.status != 'approved':
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(404)
    video_embed_url = build_youtube_embed(flat.video_url)
    video_watch_url = build_youtube_watch(flat.video_url)
    return render_template(
        'flat_detail.html',
        flat=flat,
        video_embed_url=video_embed_url,
        video_watch_url=video_watch_url,
        meta_description=summarize_text(flat.description) or app.config['DEFAULT_META_DESCRIPTION'],
        meta_image=flat.image_url or app.config['DEFAULT_OG_IMAGE'],
        meta_type='article',
    )

@app.route('/interior/<int:id>')
def interior_detail(id):
    service = InteriorService.query.get_or_404(id)
    if service.status != 'approved':
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(404)
    return render_template(
        'interior_detail.html',
        service=service,
        meta_description=summarize_text(service.description) or app.config['DEFAULT_META_DESCRIPTION'],
        meta_image=service.image_url or app.config['DEFAULT_OG_IMAGE'],
        meta_type='article',
    )

@app.route(f'/{ADMIN_PATH}/approve/<item_type>/<int:id>', methods=['POST'])
@admin_required
@limiter.limit("30 per minute")
def approve_listing(item_type, id):
    item = get_listing_item(item_type, id)
    item.status = 'approved'
    db.session.commit()
    flash('Listing approved!')
    return redirect(url_for('admin_dashboard'))

@app.route(f'/{ADMIN_PATH}/delete/<item_type>/<int:id>', methods=['POST'])
@admin_required
@limiter.limit("20 per minute")
def delete_listing(item_type, id):
    item = get_listing_item(item_type, id)
    db.session.delete(item)
    db.session.commit()
    flash('Listing deleted!')
    return redirect(url_for('admin_dashboard'))

@app.route(f'/{ADMIN_PATH}/status/<item_type>/<int:id>', methods=['POST'])
@admin_required
@limiter.limit("60 per minute")
def update_listing_status(item_type, id):
    status = normalize_status(request.form.get('status'))
    if not status:
        abort(400)
    item = get_listing_item(item_type, id)
    item.status = status
    db.session.commit()
    flash('Listing status updated!', 'success')
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.route('/contact', methods=['POST'])
@limiter.limit("10 per hour")
def contact():
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip().lower()
    contact_info = request.form.get('contact', '').strip()
    interest = request.form.get('interest', '').strip()
    message = request.form.get('message', '').strip()
    budget = request.form.get('budget', '').strip()

    if contact_info and not phone and not email:
        if '@' in contact_info:
            email = contact_info.lower()
        else:
            phone = contact_info

    if budget:
        message = f"Budget: {budget}\n{message}" if message else f"Budget: {budget}"

    if not name or not message or (not phone and not email):
        flash('Please provide your name, a message, and a phone or email.', 'warning')
        return redirect(request.referrer or url_for('index'))

    lead = Lead(
        name=name,
        phone=phone,
        email=email,
        interest=interest,
        message=message,
        status='new',
    )
    db.session.add(lead)
    db.session.commit()
    flash('Thanks! We will contact you shortly.', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route(f'/{ADMIN_PATH}/leads/<int:id>/status', methods=['POST'])
@admin_required
@limiter.limit("60 per minute")
def update_lead_status(id):
    status = normalize_lead_status(request.form.get('status'))
    if not status:
        abort(400)
    lead = Lead.query.get_or_404(id)
    lead.status = status
    db.session.commit()
    flash('Lead status updated!', 'success')
    return redirect(request.referrer or url_for('admin_dashboard', tab='leads'))

@app.route(f'/{ADMIN_PATH}/leads/<int:id>/delete', methods=['POST'])
@admin_required
@limiter.limit("30 per minute")
def delete_lead(id):
    lead = Lead.query.get_or_404(id)
    db.session.delete(lead)
    db.session.commit()
    flash('Lead deleted!', 'success')
    return redirect(request.referrer or url_for('admin_dashboard', tab='leads'))

@app.route(f'/{ADMIN_PATH}/bulk/<item_type>', methods=['POST'])
@admin_required
@limiter.limit("30 per minute")
def bulk_update_listings(item_type):
    action = request.form.get('action', '').strip().lower()
    ids = [coerce_int(value, 0) for value in request.form.getlist('ids')]
    ids = [item_id for item_id in ids if item_id > 0]
    if not ids:
        flash('Select at least one listing.', 'warning')
        return redirect(request.referrer or url_for('admin_dashboard'))

    if item_type == 'flat':
        model = Flat
        redirect_tab = 'flats'
    elif item_type == 'interior':
        model = InteriorService
        redirect_tab = 'services'
    else:
        abort(404)

    query = model.query.filter(model.id.in_(ids))
    if action in LISTING_STATUSES:
        query.update({'status': action}, synchronize_session=False)
        db.session.commit()
        flash('Listings updated!', 'success')
    elif action == 'delete':
        query.delete(synchronize_session=False)
        db.session.commit()
        flash('Listings deleted!', 'success')
    else:
        abort(400)
    return redirect(request.referrer or url_for('admin_dashboard', tab=redirect_tab))

@app.route(f'/{ADMIN_PATH}/leads/bulk', methods=['POST'])
@admin_required
@limiter.limit("30 per minute")
def bulk_update_leads():
    action = request.form.get('action', '').strip().lower()
    ids = [coerce_int(value, 0) for value in request.form.getlist('ids')]
    ids = [item_id for item_id in ids if item_id > 0]
    if not ids:
        flash('Select at least one lead.', 'warning')
        return redirect(request.referrer or url_for('admin_dashboard', tab='leads'))

    query = Lead.query.filter(Lead.id.in_(ids))
    if action in LEAD_STATUSES:
        query.update({'status': action}, synchronize_session=False)
        db.session.commit()
        flash('Leads updated!', 'success')
    elif action == 'delete':
        query.delete(synchronize_session=False)
        db.session.commit()
        flash('Leads deleted!', 'success')
    else:
        abort(400)
    return redirect(request.referrer or url_for('admin_dashboard', tab='leads'))

@app.route(f'/{ADMIN_PATH}/edit/<item_type>/<int:id>', methods=['GET', 'POST'])
@admin_required
@limiter.limit("60 per minute")
def edit_listing(item_type, id):
    item = get_listing_item(item_type, id)

    if request.method == 'POST':
        status = normalize_status(request.form.get('status'))
        if status:
            item.status = status

        image_file = request.files.get('image_file')
        uploaded_url = save_uploaded_image(image_file)
        if image_file and image_file.filename and not uploaded_url:
            flash('Unsupported image type. Use PNG, JPG, or WEBP.', 'warning')
        image_url = request.form.get('image_url', '').strip()
        if uploaded_url:
            item.image_url = uploaded_url
        elif image_url:
            item.image_url = image_url

        if item_type == 'flat':
            item.title = request.form.get('title', '').strip()
            item.location = request.form.get('location', '').strip()
            item.description = request.form.get('description', '').strip()
            item.price = coerce_float(request.form.get('price'), item.price or 0)
            item.bhk = coerce_int(request.form.get('bhk'), item.bhk or 1)
            item.area_sqft = coerce_int(request.form.get('area_sqft'), item.area_sqft or 0)
            raw_video_url = request.form.get('video_url', '').strip()
            if raw_video_url:
                if extract_youtube_id(raw_video_url):
                    item.video_url = raw_video_url
                else:
                    flash('Invalid YouTube link. Keeping the previous video.', 'warning')
            else:
                item.video_url = None
        else:
            item.provider_name = request.form.get('provider_name', '').strip()
            item.service_type = request.form.get('service_type', '').strip()
            item.description = request.form.get('description', '').strip()
            item.portfolio_url = request.form.get('portfolio_url', '').strip()
            item.starting_price = coerce_float(request.form.get('starting_price'), item.starting_price or 0)

        db.session.commit()
        flash('Listing updated successfully!', 'success')
        return redirect(url_for('admin_dashboard', tab='flats' if item_type == 'flat' else 'services'))

    template = 'admin_edit_flat.html' if item_type == 'flat' else 'admin_edit_service.html'
    return render_template(template, item=item)

# Admin Routes
@app.route(f'/{ADMIN_PATH}', strict_slashes=False)
@admin_required
def admin_dashboard():
    
    tab = request.args.get('tab', 'dashboard')
    status_filter = request.args.get('status', 'all').strip().lower()
    search = request.args.get('q', '').strip()
    if tab == 'leads' and status_filter not in LEAD_STATUSES:
        status_filter = 'all'
    if tab != 'leads' and status_filter not in LISTING_STATUSES:
        status_filter = 'all'

    flats_all = []
    services_all = []
    leads_all = []

    if tab in {'dashboard', 'flats'}:
        flats_query = Flat.query.options(joinedload(Flat.owner))
        if status_filter in LISTING_STATUSES:
            flats_query = flats_query.filter_by(status=status_filter)
        if search:
            like = f"%{search}%"
            flats_query = flats_query.filter(or_(Flat.title.ilike(like), Flat.location.ilike(like)))
        flats_all = flats_query.order_by(Flat.created_at.desc()).all()

    if tab in {'dashboard', 'services'}:
        services_query = InteriorService.query.options(joinedload(InteriorService.provider))
        if status_filter in LISTING_STATUSES:
            services_query = services_query.filter_by(status=status_filter)
        if search:
            like = f"%{search}%"
            services_query = services_query.filter(InteriorService.provider_name.ilike(like))
        services_all = services_query.order_by(InteriorService.created_at.desc()).all()

    if tab == 'leads':
        leads_query = Lead.query
        if status_filter in LEAD_STATUSES:
            leads_query = leads_query.filter_by(status=status_filter)
        if search:
            like = f"%{search}%"
            leads_query = leads_query.filter(
                or_(
                    Lead.name.ilike(like),
                    Lead.email.ilike(like),
                    Lead.phone.ilike(like),
                    Lead.message.ilike(like),
                )
            )
        leads_all = leads_query.order_by(Lead.created_at.desc()).all()

    stats = get_cached_value(
        'admin_stats',
        30,
        lambda: {
            'total_flats': Flat.query.count(),
            'pending_flats': Flat.query.filter_by(status='pending').count(),
            'approved_flats': Flat.query.filter_by(status='approved').count(),
            'rejected_flats': Flat.query.filter_by(status='rejected').count(),
            'total_services': InteriorService.query.count(),
            'pending_services': InteriorService.query.filter_by(status='pending').count(),
            'approved_services': InteriorService.query.filter_by(status='approved').count(),
            'rejected_services': InteriorService.query.filter_by(status='rejected').count(),
            'total_leads': Lead.query.count(),
            'new_leads': Lead.query.filter_by(status='new').count(),
        },
    )
    admin_filters = {
        'status': status_filter,
        'q': search,
    }
    if tab == 'leads':
        filters_applied = bool(search or status_filter in LEAD_STATUSES)
        status_options = [
            ('all', 'All Status'),
            ('new', 'New'),
            ('contacted', 'Contacted'),
            ('closed', 'Closed'),
        ]
    else:
        filters_applied = bool(search or status_filter in LISTING_STATUSES)
        status_options = [
            ('all', 'All Status'),
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ]
    
    return render_template('admin_dashboard.html', 
                            flats=flats_all, 
                            services=services_all,
                            leads=leads_all,
                            active_tab=tab,
                            stats=stats,
                            admin_filters=admin_filters,
                            filters_applied=filters_applied,
                            status_options=status_options)

@app.route('/flats')
def flats():
    search = request.args.get('search', '').strip()
    bhk = request.args.get('bhk', 'all').strip()
    min_price = request.args.get('min_price', '').strip()
    max_price = request.args.get('max_price', '').strip()
    sort = request.args.get('sort', 'newest').strip()
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    per_page = app.config['LISTINGS_PER_PAGE']
    sort_options = {
        'newest': Flat.created_at.desc(),
        'price_low': Flat.price.asc(),
        'price_high': Flat.price.desc(),
        'area_high': Flat.area_sqft.desc(),
    }
    if sort not in sort_options:
        sort = 'newest'

    query = Flat.query.filter_by(status='approved').options(
        load_only(
            Flat.id,
            Flat.title,
            Flat.location,
            Flat.price,
            Flat.bhk,
            Flat.area_sqft,
            Flat.image_url,
            Flat.created_at,
        )
    )

    if search:
        like = f"%{search}%"
        query = query.filter(or_(Flat.location.ilike(like), Flat.title.ilike(like)))

    if bhk and bhk != 'all':
        if bhk == '4plus':
            query = query.filter(Flat.bhk >= 4)
        else:
            try:
                bhk_value = int(bhk)
            except ValueError:
                bhk_value = None
            if bhk_value:
                query = query.filter(Flat.bhk == bhk_value)

    try:
        min_price_value = float(min_price) if min_price else None
    except ValueError:
        min_price_value = None

    try:
        max_price_value = float(max_price) if max_price else None
    except ValueError:
        max_price_value = None

    if min_price_value is not None:
        query = query.filter(Flat.price >= min_price_value)
    if max_price_value is not None:
        query = query.filter(Flat.price <= max_price_value)

    total_results = query.order_by(None).count()
    sort_clause = sort_options[sort]
    if sort == 'newest':
        query = query.order_by(sort_clause)
    else:
        query = query.order_by(sort_clause, Flat.created_at.desc())
    offset = (page - 1) * per_page
    flats_page = query.offset(offset).limit(per_page + 1).all()
    has_next = len(flats_page) > per_page
    has_prev = page > 1
    all_flats = flats_page[:per_page]
    filters = {
        'search': search,
        'bhk': bhk,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort,
    }
    filters_applied = bool(search or (bhk and bhk != 'all') or min_price or max_price)
    filter_params = {}
    if search:
        filter_params['search'] = search
    if bhk and bhk != 'all':
        filter_params['bhk'] = bhk
    if min_price:
        filter_params['min_price'] = min_price
    if max_price:
        filter_params['max_price'] = max_price
    if sort and sort != 'newest':
        filter_params['sort'] = sort
    prev_url = url_for('flats', page=page - 1, **filter_params) if has_prev else None
    next_url = url_for('flats', page=page + 1, **filter_params) if has_next else None
    return render_template(
        'flats.html',
        flats=all_flats,
        filters=filters,
        filters_applied=filters_applied,
        total_results=total_results,
        sort=sort,
        page=page,
        has_prev=has_prev,
        has_next=has_next,
        prev_url=prev_url,
        next_url=next_url,
        meta_description='Browse verified flats for sale in Bangladesh with advanced filters and direct contact options.',
        meta_image=app.config['DEFAULT_OG_IMAGE'],
    )

@app.route('/interior')
def interior():
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    per_page = app.config['LISTINGS_PER_PAGE']
    query = InteriorService.query.filter_by(status='approved').options(
        load_only(
            InteriorService.id,
            InteriorService.provider_name,
            InteriorService.service_type,
            InteriorService.description,
            InteriorService.starting_price,
            InteriorService.image_url,
            InteriorService.created_at,
        )
    )
    query = query.order_by(InteriorService.created_at.desc())
    offset = (page - 1) * per_page
    services_page = query.offset(offset).limit(per_page + 1).all()
    has_next = len(services_page) > per_page
    has_prev = page > 1
    services = services_page[:per_page]
    prev_url = url_for('interior', page=page - 1) if has_prev else None
    next_url = url_for('interior', page=page + 1) if has_next else None
    return render_template(
        'interior.html',
        services=services,
        page=page,
        has_prev=has_prev,
        has_next=has_next,
        prev_url=prev_url,
        next_url=next_url,
        meta_description='Discover interior design studios and portfolios with clear scope, pricing, and timelines.',
        meta_image=app.config['DEFAULT_OG_IMAGE'],
    )

@app.route('/post-listing', methods=['GET', 'POST'])
@admin_required
@limiter.limit("30 per hour")
def post_listing():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        status = 'pending'
        image_file = request.files.get('image_file')
        uploaded_url = save_uploaded_image(image_file)
        if image_file and image_file.filename and not uploaded_url:
            flash('Unsupported image type. Use PNG, JPG, or WEBP.', 'warning')

        if form_type == 'flat':
            raw_video_url = request.form.get('video_url', '').strip()
            video_url = raw_video_url if extract_youtube_id(raw_video_url) else None
            if raw_video_url and not video_url:
                flash('Invalid YouTube link. Video has been skipped.', 'warning')
            new_flat = Flat(
                title=request.form.get('title', '').strip(),
                location=request.form.get('location', '').strip(),
                price=coerce_float(request.form.get('price'), 0),
                bhk=coerce_int(request.form.get('bhk'), 1),
                area_sqft=coerce_int(request.form.get('area'), 0),
                description=request.form.get('description', '').strip(),
                image_url=uploaded_url or request.form.get('image_url', '').strip(),
                video_url=video_url,
                user_id=current_user.id
            )
            new_flat.status = status
                
            db.session.add(new_flat)
        elif form_type == 'interior':
            new_service = InteriorService(
                provider_name=request.form.get('provider_name', '').strip(),
                service_type=request.form.get('service_type', '').strip(),
                starting_price=coerce_float(request.form.get('starting_price'), 0),
                description=request.form.get('description', '').strip(),
                portfolio_url=request.form.get('portfolio_url', '').strip(),
                image_url=uploaded_url or request.form.get('image_url', '').strip(),
                user_id=current_user.id
            )
            new_service.status = status
                
            db.session.add(new_service)
        else:
            abort(400)
        
        db.session.commit()
        flash('Listing posted successfully!', 'success')
        return redirect(url_for('admin_dashboard', tab='flats' if form_type == 'flat' else 'services'))
    return render_template('post_listing.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)

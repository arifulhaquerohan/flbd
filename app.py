import os
from datetime import timedelta
from flask import Flask, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

from models import db, User
from extensions import csrf, compress, limiter, login_manager, mail
from blueprints.public import public_bp
from blueprints.admin import admin_bp


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

app = Flask(__name__, instance_path=resolve_instance_path())

if os.getenv('TRUST_PROXY', '0') == '1':
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

secret_key = os.getenv('SECRET_KEY')
if not secret_key:
    secret_key = os.urandom(32)
    
app.config['SECRET_KEY'] = secret_key
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', '0') == '1'
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
app.config['REMEMBER_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', '0') == '1'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=6)
app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024
app.config['WTF_CSRF_TIME_LIMIT'] = int(os.getenv('WTF_CSRF_TIME_LIMIT', '3600'))
app.config['WTF_CSRF_SSL_STRICT'] = True
app.config['COMPRESS_MIN_SIZE'] = int(os.getenv('COMPRESS_MIN_SIZE', '512'))
app.config['COMPRESS_LEVEL'] = int(os.getenv('COMPRESS_LEVEL', '6'))
app.config['COMPRESS_MIMETYPES'] = ['text/html', 'text/css', 'application/javascript', 'application/json', 'application/xml', 'text/xml', 'text/plain', 'image/svg+xml']

database_url = os.getenv('DATABASE_URL', 'sqlite:///flatland.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True, 'pool_recycle': 280}
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000
app.config['LISTINGS_PER_PAGE'] = int(os.getenv('LISTINGS_PER_PAGE', '9'))
app.config['ADMIN_DASHBOARD_RECENT_LIMIT'] = int(os.getenv('ADMIN_DASHBOARD_RECENT_LIMIT', '8'))
app.config['ADMIN_LISTINGS_PER_PAGE'] = int(os.getenv('ADMIN_LISTINGS_PER_PAGE', '20'))
app.config['ALLOWED_IMAGE_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'webp'}
app.config['MAX_GALLERY_IMAGES'] = int(os.getenv('MAX_GALLERY_IMAGES', '10'))
app.config['DEFAULT_META_DESCRIPTION'] = 'FlatlandBD is a trusted platform for buying and selling flats, plus premium interior design services in Bangladesh.'
app.config['DEFAULT_OG_IMAGE'] = os.getenv('DEFAULT_OG_IMAGE', 'https://images.unsplash.com/photo-1505691938895-1758d7feb511?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=80')

# Flask Mail config
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', '1']
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
app.config['ADMIN_EMAIL'] = os.getenv('ADMIN_EMAIL')
app.config['ADMIN_PATH'] = os.getenv('ADMIN_PATH', 'admin').strip().strip('/') or 'admin'

# Init extensions
db.init_app(app)
compress.init_app(app)
csrf.init_app(app)
limiter.init_app(app)
mail.init_app(app)
login_manager.init_app(app)

login_manager.login_view = 'public.login'
login_manager.session_protection = "strong"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def static_url(filename):
    from flask import url_for
    if not filename: return ''
    file_path = os.path.join(app.static_folder, filename)
    try: version = int(os.path.getmtime(file_path))
    except OSError: version = None
    return url_for('static', filename=filename, v=version) if version else url_for('static', filename=filename)

app.jinja_env.globals['static_url'] = static_url

@app.context_processor
def override_url_for():
    from flask import url_for as _url_for
    def custom_url_for(endpoint, **values):
        if endpoint and "." not in endpoint and endpoint != "static":
            admin_endpoints = {'admin_dashboard', 'approve_listing', 'delete_listing', 'update_listing_status', 'update_lead_status', 'delete_lead', 'bulk_update_listings', 'bulk_update_leads', 'edit_listing', 'post_listing', 'export_data', 'preview'}
            if endpoint in admin_endpoints:
                endpoint = f"admin.{endpoint}"
            else:
                endpoint = f"public.{endpoint}"
        return _url_for(endpoint, **values)
    return dict(url_for=custom_url_for)

@app.context_processor
def inject_meta_defaults():
    return {
        'default_meta_description': app.config['DEFAULT_META_DESCRIPTION'],
        'default_og_image': app.config['DEFAULT_OG_IMAGE'],
    }

@app.after_request
def add_security_headers(response):
    csp_parts = [
        "default-src 'self'", "base-uri 'self'", "object-src 'none'", "frame-ancestors 'self'", "form-action 'self'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com", "img-src 'self' data: https:",
        "frame-src 'self' https://www.google.com https://maps.google.com https://maps.gstatic.com https://www.youtube.com https://www.youtube-nocookie.com",
        "connect-src 'self'",
    ]
    response.headers.setdefault('Content-Security-Policy', '; '.join(csp_parts))
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=(), payment=()')
    
    current_user_auth = False
    try:
        from flask_login import current_user
        current_user_auth = current_user.is_authenticated
    except Exception:
        pass
    request_secure = request.is_secure if request else False
    if request_secure:
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        
    path = request.path if request else '/'
    endpoint = request.endpoint if request else None

    PUBLIC_CACHE_ENDPOINTS = {'public.index', 'public.flats', 'public.interior', 'public.flat_detail', 'public.interior_detail', 'public.robots', 'public.sitemap'}
    if path.startswith('/static/'): response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif path.startswith(f"/{app.config['ADMIN_PATH']}") or current_user_auth: response.headers['Cache-Control'] = 'no-store'
    
    if request.method == 'GET' and not current_user_auth and not response.headers.get('Set-Cookie') and endpoint in PUBLIC_CACHE_ENDPOINTS:
        ttl = 3600 if endpoint in {'public.robots', 'public.sitemap'} else 120
        response.headers.setdefault('Cache-Control', f'public, max-age={ttl}, stale-while-revalidate={ttl // 2}')
        
    vary = response.headers.get('Vary')
    if vary:
        if 'Accept-Encoding' not in vary: response.headers['Vary'] = f'{vary}, Accept-Encoding'
    else: response.headers['Vary'] = 'Accept-Encoding'
    return response

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Register Blueprints
app.register_blueprint(public_bp)
app.register_blueprint(admin_bp, url_prefix=f"/{app.config['ADMIN_PATH']}")

with app.app_context():
    db.create_all()

    # Create admin if missing
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
    if not User.query.filter_by(role='admin').first():
        if ADMIN_EMAIL and ADMIN_PASSWORD:
            admin = User(username=ADMIN_USERNAME, email=ADMIN_EMAIL, role='admin')
            admin.set_password(ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.commit()
            print("Admin user created from environment variables.")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)
# Force HTTPS cookies when behind HTTPS terminators.
if os.getenv('FORCE_HTTPS', '0') == '1':
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['REMEMBER_COOKIE_SECURE'] = True

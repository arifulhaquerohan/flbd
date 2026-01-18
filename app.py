import os
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models import db, User, Flat, InteriorService
from sqlalchemy import or_

from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
Compress(app)
csrf = CSRFProtect(app)

# Brute-force protection
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-7755')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', '0') == '1'
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
app.config['REMEMBER_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', '0') == '1'

# Secure Admin Path from .env
ADMIN_PATH = os.getenv('ADMIN_PATH', 'admin')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

# Database configuration
database_url = os.getenv('DATABASE_URL', 'sqlite:///flatland.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000 # Cache static files for 1 year

db.init_app(app)

# Login Manager Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = "strong"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def require_admin():
    if not current_user.is_authenticated or current_user.role != 'admin':
        abort(404)

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
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute") # Max 5 attempts per minute to prevent brute-force
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower() # Force lowercase for database consistency
        password = request.form.get('password', '')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter(User.email.ilike(email)).first() # Case-insensitive search
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/flat/<int:id>')
def flat_detail(id):
    flat = Flat.query.get_or_404(id)
    return render_template('flat_detail.html', flat=flat)

@app.route('/interior/<int:id>')
def interior_detail(id):
    service = InteriorService.query.get_or_404(id)
    return render_template('interior_detail.html', service=service)

@app.route(f'/{ADMIN_PATH}/approve/<type>/<int:id>')
def approve_listing(type, id):
    require_admin()
    
    if type == 'flat':
        item = Flat.query.get_or_404(id)
    else:
        item = InteriorService.query.get_or_404(id)
    
    item.status = 'approved'
    db.session.commit()
    flash('Listing approved!')
    return redirect(url_for('admin_dashboard'))

@app.route(f'/{ADMIN_PATH}/delete/<type>/<int:id>')
def delete_listing(type, id):
    require_admin()
    
    if type == 'flat':
        item = Flat.query.get_or_404(id)
    else:
        item = InteriorService.query.get_or_404(id)
    
    db.session.delete(item)
    db.session.commit()
    flash('Listing deleted!')
    return redirect(url_for('admin_dashboard'))

# Admin Routes
@app.route(f'/{ADMIN_PATH}')
def admin_dashboard():
    require_admin()
    
    tab = request.args.get('tab', 'dashboard')
    status_filter = request.args.get('status', 'all').strip().lower()
    search = request.args.get('q', '').strip()

    flats_query = Flat.query
    services_query = InteriorService.query

    if status_filter in {'pending', 'approved'}:
        flats_query = flats_query.filter_by(status=status_filter)
        services_query = services_query.filter_by(status=status_filter)

    if search:
        like = f"%{search}%"
        flats_query = flats_query.filter(or_(Flat.title.ilike(like), Flat.location.ilike(like)))
        services_query = services_query.filter(InteriorService.provider_name.ilike(like))

    flats_all = flats_query.order_by(Flat.created_at.desc()).all()
    services_all = services_query.order_by(InteriorService.created_at.desc()).all()

    stats = {
        'total_flats': Flat.query.count(),
        'pending_flats': Flat.query.filter_by(status='pending').count(),
        'approved_flats': Flat.query.filter_by(status='approved').count(),
        'total_services': InteriorService.query.count(),
        'pending_services': InteriorService.query.filter_by(status='pending').count(),
        'approved_services': InteriorService.query.filter_by(status='approved').count(),
    }
    admin_filters = {
        'status': status_filter,
        'q': search,
    }
    filters_applied = bool(search or status_filter in {'pending', 'approved'})
    
    return render_template('admin_dashboard.html', 
                            flats=flats_all, 
                            services=services_all,
                            active_tab=tab,
                            stats=stats,
                            admin_filters=admin_filters,
                            filters_applied=filters_applied)

@app.route('/flats')
def flats():
    search = request.args.get('search', '').strip()
    bhk = request.args.get('bhk', 'all').strip()
    min_price = request.args.get('min_price', '').strip()
    max_price = request.args.get('max_price', '').strip()

    query = Flat.query.filter_by(status='approved')

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

    all_flats = query.order_by(Flat.created_at.desc()).all()
    filters = {
        'search': search,
        'bhk': bhk,
        'min_price': min_price,
        'max_price': max_price,
    }
    filters_applied = bool(search or (bhk and bhk != 'all') or min_price or max_price)
    return render_template('flats.html', flats=all_flats, filters=filters, filters_applied=filters_applied)

@app.route('/interior')
def interior():
    services = InteriorService.query.filter_by(status='approved').order_by(InteriorService.created_at.desc()).all()
    return render_template('interior.html', services=services)

@app.route('/post-listing', methods=['GET', 'POST'])
def post_listing():
    require_admin()
    
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        # Default to admin user as owner for guest posts
        admin_user = User.query.filter_by(role='admin').first()
        admin_id = admin_user.id if admin_user else 1

        if form_type == 'flat':
            new_flat = Flat(
                title=request.form.get('title'),
                location=request.form.get('location'),
                price=float(request.form.get('price') or 0),
                bhk=int(request.form.get('bhk') or 1),
                area_sqft=int(request.form.get('area') or 0),
                description=request.form.get('description'),
                image_url=request.form.get('image_url'),
                user_id=current_user.id if current_user.is_authenticated else admin_id
            )
            # Admin posts are auto-approved
            if current_user.is_authenticated and current_user.role == 'admin':
                new_flat.status = 'approved'
            else:
                new_flat.status = 'pending'
                
            db.session.add(new_flat)
        else:
            new_service = InteriorService(
                provider_name=request.form.get('provider_name'),
                service_type=request.form.get('service_type'),
                starting_price=float(request.form.get('starting_price') or 0),
                description=request.form.get('description'),
                portfolio_url=request.form.get('portfolio_url'),
                image_url=request.form.get('image_url'),
                user_id=current_user.id if current_user.is_authenticated else admin_id
            )
            if current_user.is_authenticated and current_user.role == 'admin':
                new_service.status = 'approved'
            else:
                new_service.status = 'pending'
                
            db.session.add(new_service)
        
        db.session.commit()
        msg = 'Listing posted! It will be live after admin approval.'
        if current_user.is_authenticated and current_user.role == 'admin':
            msg = 'Listing posted successfully! It is now live.'
        
        flash(msg)
        return redirect(url_for('index'))
    return render_template('post_listing.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)

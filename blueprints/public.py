from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, Response, current_app
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.orm import load_only, selectinload
from flask_mail import Message

from models import db, User, Flat, InteriorService, FlatImage, InteriorImage, Lead
from forms import LoginForm, ContactForm
from extensions import limiter, mail
from utils import get_cached_value, extract_youtube_id, build_youtube_embed, build_youtube_watch, summarize_text

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index():
    stats = get_cached_value(
        'public_stats', 60,
        lambda: {
            'flats': Flat.query.filter_by(status='approved').count(),
            'studios': InteriorService.query.filter_by(status='approved').count(),
        }
    )
    return render_template(
        'index.html',
        stats=stats,
        meta_description=current_app.config['DEFAULT_META_DESCRIPTION'],
        meta_image=current_app.config['DEFAULT_OG_IMAGE'],
    )

@public_bp.route('/robots.txt')
def robots():
    admin_path = current_app.config.get('ADMIN_PATH', 'admin')
    rules = [
        'User-agent: *',
        f'Disallow: /{admin_path}',
        'Disallow: /preview',
        'Disallow: /login',
        'Disallow: /post-listing',
        f'Sitemap: {url_for("public.sitemap", _external=True)}',
    ]
    return Response('\n'.join(rules), mimetype='text/plain')

@public_bp.route('/sitemap.xml')
def sitemap():
    pages = []
    today = datetime.utcnow().date().isoformat()
    static_pages = ['public.index', 'public.flats', 'public.interior', 'public.login']
    for endpoint in static_pages:
        pages.append({'loc': url_for(endpoint, _external=True), 'lastmod': today})

    flats = Flat.query.filter_by(status='approved').with_entities(Flat.id, Flat.created_at).all()
    for flat_id, created_at in flats:
        lastmod = created_at.date().isoformat() if created_at else today
        pages.append({'loc': url_for('public.flat_detail', id=flat_id, _external=True), 'lastmod': lastmod})

    services = InteriorService.query.filter_by(status='approved').with_entities(
        InteriorService.id, InteriorService.created_at
    ).all()
    for service_id, created_at in services:
        lastmod = created_at.date().isoformat() if created_at else today
        pages.append({'loc': url_for('public.interior_detail', id=service_id, _external=True), 'lastmod': lastmod})

    xml = render_template('sitemap.xml', pages=pages)
    return Response(xml, mimetype='application/xml')

@public_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('public.index'))
        
    form = LoginForm()
    if request.method == 'POST':
        # Using WTF form validation if possible
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter(User.email.ilike(email)).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('public.index'))
        
        flash('Invalid email or password', 'danger')
    return render_template(
        'login.html',
        meta_description='Admin login for FlatlandBD.',
        meta_type='website',
    )

@public_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('public.index'))

@public_bp.route('/signup')
@limiter.limit("3 per minute")
def signup():
    abort(404)

@public_bp.route('/contact', methods=['POST'])
@limiter.limit("10 per hour")
def contact():
    form = ContactForm()
    
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip().lower()
    contact_info = request.form.get('contact', '').strip() # Fallback
    interest = request.form.get('interest', '').strip()
    message = request.form.get('message', '').strip()
    budget = request.form.get('budget', '').strip()
    service_type = request.form.get('service_type', '').strip()
    timeline = request.form.get('timeline', '').strip()

    if contact_info and not phone and not email:
        if '@' in contact_info:
            email = contact_info.lower()
        else:
            phone = contact_info

    meta_lines = []
    if budget: meta_lines.append(f"Budget: {budget}")
    if service_type: meta_lines.append(f"Service: {service_type}")
    if timeline: meta_lines.append(f"Timeline: {timeline}")
    if meta_lines: message = "\n".join(meta_lines + ([message] if message else []))

    if not name or not message:
        flash('Please provide your name and a message.', 'warning')
        return redirect(request.referrer or url_for('public.index'))

    if not phone and not email:
        flash('Please provide a contact number or email.', 'warning')
        return redirect(request.referrer or url_for('public.index'))

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
    
    # 2. EMAIL NOTIFICATIONS (Send email if mail is configured)
    try:
        if current_app.config.get('MAIL_SERVER') and current_app.config.get('ADMIN_EMAIL'):
            msg = Message(
                subject=f"New Lead from {name} - FlatlandBD",
                sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
                recipients=[current_app.config.get('ADMIN_EMAIL')],
                body=f"New Contact Formulation:\nName: {name}\nPhone: {phone}\nEmail: {email}\nInterest: {interest}\n\nMessage:\n{message}"
            )
            mail.send(msg)
    except Exception as e:
        print("Mail sending failed:", e)

    flash('Thanks! We will contact you shortly.', 'success')
    return redirect(request.referrer or url_for('public.index'))

@public_bp.route('/flat/<int:id>')
def flat_detail(id):
    flat = Flat.query.options(
        load_only(Flat.id, Flat.title, Flat.description, Flat.price, Flat.location, Flat.area_sqft, Flat.bhk, Flat.image_url, Flat.video_url, Flat.status),
        selectinload(Flat.images).load_only(FlatImage.id, FlatImage.image_url),
    ).get_or_404(id)
    if flat.status != 'approved':
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(404)
    return render_template(
        'flat_detail.html',
        flat=flat,
        video_embed_url=build_youtube_embed(flat.video_url),
        video_watch_url=build_youtube_watch(flat.video_url),
        meta_description=summarize_text(flat.description) or current_app.config['DEFAULT_META_DESCRIPTION'],
        meta_image=flat.image_url or current_app.config['DEFAULT_OG_IMAGE'],
        meta_type='article',
    )

@public_bp.route('/interior/<int:id>')
def interior_detail(id):
    service = InteriorService.query.options(
        load_only(InteriorService.id, InteriorService.provider_name, InteriorService.service_type, InteriorService.description, InteriorService.starting_price, InteriorService.image_url, InteriorService.portfolio_url, InteriorService.status),
        selectinload(InteriorService.images).load_only(InteriorImage.id, InteriorImage.image_url),
    ).get_or_404(id)
    if service.status != 'approved':
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(404)
    return render_template(
        'interior_detail.html',
        service=service,
        meta_description=summarize_text(service.description) or current_app.config['DEFAULT_META_DESCRIPTION'],
        meta_image=service.image_url or current_app.config['DEFAULT_OG_IMAGE'],
        meta_type='article',
    )

@public_bp.route('/flats')
def flats():
    search = request.args.get('search', '').strip()
    bhk = request.args.get('bhk', 'all').strip()
    min_price = request.args.get('min_price', '').strip()
    max_price = request.args.get('max_price', '').strip()
    sort = request.args.get('sort', 'newest').strip()
    page = request.args.get('page', 1, type=int)
    if page < 1: page = 1
    
    per_page = current_app.config['LISTINGS_PER_PAGE']
    sort_options = {
        'newest': Flat.created_at.desc(),
        'price_low': Flat.price.asc(),
        'price_high': Flat.price.desc(),
        'area_high': Flat.area_sqft.desc(),
    }
    if sort not in sort_options: sort = 'newest'

    query = Flat.query.filter_by(status='approved').options(
        load_only(Flat.id, Flat.title, Flat.location, Flat.price, Flat.bhk, Flat.area_sqft, Flat.image_url, Flat.created_at)
    )

    if search:
        like = f"%{search}%"
        query = query.filter(or_(Flat.location.ilike(like), Flat.title.ilike(like)))

    if bhk and bhk != 'all':
        if bhk == '4plus': query = query.filter(Flat.bhk >= 4)
        else:
            try:
                if int(bhk): query = query.filter(Flat.bhk == int(bhk))
            except ValueError: pass

    try: min_price_val = float(min_price) if min_price else None
    except ValueError: min_price_val = None
    if min_price_val is not None: query = query.filter(Flat.price >= min_price_val)

    try: max_price_val = float(max_price) if max_price else None
    except ValueError: max_price_val = None
    if max_price_val is not None: query = query.filter(Flat.price <= max_price_val)

    sort_clause = sort_options[sort]
    if sort == 'newest': query = query.order_by(sort_clause)
    else: query = query.order_by(sort_clause, Flat.created_at.desc())
    
    offset = (page - 1) * per_page
    flats_page = query.offset(offset).limit(per_page + 1).all()
    has_next = len(flats_page) > per_page
    has_prev = page > 1
    all_flats = flats_page[:per_page]
    
    filters = {'search': search, 'bhk': bhk, 'min_price': min_price, 'max_price': max_price, 'sort': sort}
    filters_applied = bool(search or (bhk and bhk != 'all') or min_price or max_price)
    
    filter_params = {k: v for k, v in filters.items() if v and v != 'all' and v != 'newest'}
    prev_url = url_for('public.flats', page=page - 1, **filter_params) if has_prev else None
    next_url = url_for('public.flats', page=page + 1, **filter_params) if has_next else None
    
    return render_template(
        'flats.html',
        flats=all_flats,
        filters=filters,
        filters_applied=filters_applied,
        page_listing_count=len(all_flats),
        sort=sort,
        page=page,
        has_prev=has_prev,
        has_next=has_next,
        prev_url=prev_url,
        next_url=next_url,
        meta_description='Browse verified flats for sale in Bangladesh.',
    )

@public_bp.route('/interior')
def interior():
    page = request.args.get('page', 1, type=int)
    if page < 1: page = 1
    per_page = current_app.config['LISTINGS_PER_PAGE']
    
    query = InteriorService.query.filter_by(status='approved').options(
        load_only(InteriorService.id, InteriorService.provider_name, InteriorService.service_type, InteriorService.description, InteriorService.starting_price, InteriorService.image_url, InteriorService.created_at)
    ).order_by(InteriorService.created_at.desc())
    
    offset = (page - 1) * per_page
    services_page = query.offset(offset).limit(per_page + 1).all()
    has_next = len(services_page) > per_page
    has_prev = page > 1
    services = services_page[:per_page]
    
    prev_url = url_for('public.interior', page=page - 1) if has_prev else None
    next_url = url_for('public.interior', page=page + 1) if has_next else None
    
    return render_template(
        'interior.html',
        services=services,
        page=page,
        has_prev=has_prev,
        has_next=has_next,
        prev_url=prev_url,
        next_url=next_url,
        meta_description='Discover interior design studios and portfolios.',
    )

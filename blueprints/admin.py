import csv
from io import StringIO
from flask import Blueprint, request, render_template, redirect, url_for, flash, abort, Response, current_app
from flask_login import current_user
from sqlalchemy.orm import joinedload, load_only
from sqlalchemy import or_

from models import db, User, Flat, InteriorService, FlatImage, InteriorImage, Lead
from extensions import limiter
from utils import admin_required, get_listing_item, normalize_status, normalize_lead_status, LISTING_STATUSES, LEAD_STATUSES, coerce_int, coerce_float, save_uploaded_image, parse_image_urls, extract_youtube_id, collect_uploaded_images, paginate_query, get_cached_value, collect_admin_stats, normalize_preview_path

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/export/<item_type>')
@admin_required
@limiter.limit("20 per minute")
def export_data(item_type):
    status_filter = request.args.get('status', 'all').strip().lower()
    search = request.args.get('q', '').strip()

    output = StringIO()
    writer = csv.writer(output)

    if item_type == 'flats':
        if status_filter not in LISTING_STATUSES: status_filter = 'all'
        query = Flat.query.options(joinedload(Flat.owner))
        if status_filter in LISTING_STATUSES: query = query.filter_by(status=status_filter)
        if search:
            like = f"%{search}%"
            query = query.filter(or_(Flat.title.ilike(like), Flat.location.ilike(like)))
        writer.writerow(['id', 'title', 'location', 'price', 'bhk', 'area_sqft', 'status', 'owner', 'created_at', 'image_url', 'video_url'])
        for item in query.order_by(Flat.created_at.desc()).all():
            writer.writerow([item.id, item.title, item.location, item.price, item.bhk, item.area_sqft, item.status, item.owner.username if item.owner else '', item.created_at.isoformat() if item.created_at else '', item.image_url or '', item.video_url or ''])
        filename = 'flats.csv'
    elif item_type == 'services':
        if status_filter not in LISTING_STATUSES: status_filter = 'all'
        query = InteriorService.query.options(joinedload(InteriorService.provider))
        if status_filter in LISTING_STATUSES: query = query.filter_by(status=status_filter)
        if search:
            like = f"%{search}%"
            query = query.filter(InteriorService.provider_name.ilike(like))
        writer.writerow(['id', 'provider_name', 'service_type', 'starting_price', 'status', 'provider', 'created_at', 'image_url', 'portfolio_url'])
        for item in query.order_by(InteriorService.created_at.desc()).all():
            writer.writerow([item.id, item.provider_name, item.service_type, item.starting_price, item.status, item.provider.username if item.provider else '', item.created_at.isoformat() if item.created_at else '', item.image_url or '', item.portfolio_url or ''])
        filename = 'services.csv'
    elif item_type == 'leads':
        if status_filter not in LEAD_STATUSES: status_filter = 'all'
        query = Lead.query
        if status_filter in LEAD_STATUSES: query = query.filter_by(status=status_filter)
        if search:
            like = f"%{search}%"
            query = query.filter(or_(Lead.name.ilike(like), Lead.email.ilike(like), Lead.phone.ilike(like), Lead.message.ilike(like)))
        writer.writerow(['id', 'name', 'phone', 'email', 'interest', 'message', 'status', 'created_at'])
        for item in query.order_by(Lead.created_at.desc()).all():
            writer.writerow([item.id, item.name, item.phone or '', item.email or '', item.interest or '', item.message, item.status, item.created_at.isoformat() if item.created_at else ''])
        filename = 'leads.csv'
    else:
        abort(404)

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@admin_bp.route('/', strict_slashes=False)
@admin_required
def admin_dashboard():
    tab = request.args.get('tab', 'dashboard')
    status_filter = request.args.get('status', 'all').strip().lower()
    search = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    if page < 1: page = 1
    if tab == 'leads' and status_filter not in LEAD_STATUSES: status_filter = 'all'
    if tab != 'leads' and status_filter not in LISTING_STATUSES: status_filter = 'all'

    recent_limit = current_app.config['ADMIN_DASHBOARD_RECENT_LIMIT']
    per_page = current_app.config['ADMIN_LISTINGS_PER_PAGE']
    flats_all, services_all, leads_all = [], [], []
    has_prev, has_next, prev_url, next_url = False, False, None, None

    if tab in {'dashboard', 'flats'}:
        flats_query = Flat.query.options(load_only(Flat.id, Flat.title, Flat.location, Flat.image_url, Flat.status, Flat.created_at), joinedload(Flat.owner).load_only(User.id, User.username))
        if status_filter in LISTING_STATUSES: flats_query = flats_query.filter_by(status=status_filter)
        if search:
            like = f"%{search}%"
            flats_query = flats_query.filter(or_(Flat.title.ilike(like), Flat.location.ilike(like)))
        flats_query = flats_query.order_by(Flat.created_at.desc())
        if tab == 'dashboard': flats_all = flats_query.limit(recent_limit).all()
        else: flats_all, has_prev, has_next = paginate_query(flats_query, page, per_page)

    if tab in {'dashboard', 'services'}:
        services_query = InteriorService.query.options(load_only(InteriorService.id, InteriorService.provider_name, InteriorService.service_type, InteriorService.image_url, InteriorService.status, InteriorService.created_at), joinedload(InteriorService.provider).load_only(User.id, User.username))
        if status_filter in LISTING_STATUSES: services_query = services_query.filter_by(status=status_filter)
        if search:
            like = f"%{search}%"
            services_query = services_query.filter(InteriorService.provider_name.ilike(like))
        services_query = services_query.order_by(InteriorService.created_at.desc())
        if tab == 'dashboard': services_all = services_query.limit(recent_limit).all()
        else: services_all, has_prev, has_next = paginate_query(services_query, page, per_page)

    if tab == 'leads':
        leads_query = Lead.query.options(load_only(Lead.id, Lead.name, Lead.phone, Lead.email, Lead.interest, Lead.message, Lead.status, Lead.created_at))
        if status_filter in LEAD_STATUSES: leads_query = leads_query.filter_by(status=status_filter)
        if search:
            like = f"%{search}%"
            leads_query = leads_query.filter(or_(Lead.name.ilike(like), Lead.email.ilike(like), Lead.phone.ilike(like), Lead.message.ilike(like)))
        leads_query = leads_query.order_by(Lead.created_at.desc())
        leads_all, has_prev, has_next = paginate_query(leads_query, page, per_page)

    stats = get_cached_value('admin_stats', 30, collect_admin_stats)
    admin_filters = {'status': status_filter, 'q': search}
    
    if tab in {'flats', 'services', 'leads'}:
        page_params = {'tab': tab}
        if status_filter != 'all': page_params['status'] = status_filter
        if search: page_params['q'] = search
        if has_prev: prev_url = url_for('admin.admin_dashboard', page=page - 1, **page_params)
        if has_next: next_url = url_for('admin.admin_dashboard', page=page + 1, **page_params)

    status_options = [('all', 'All Status'), ('new', 'New'), ('contacted', 'Contacted'), ('closed', 'Closed')] if tab == 'leads' else [('all', 'All Status'), ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]
    filters_applied = bool(search or status_filter in (LEAD_STATUSES if tab == 'leads' else LISTING_STATUSES))
    
    return render_template('admin_dashboard.html', flats=flats_all, services=services_all, leads=leads_all, active_tab=tab, stats=stats, admin_filters=admin_filters, filters_applied=filters_applied, status_options=status_options, page=page, has_prev=has_prev, has_next=has_next, prev_url=prev_url, next_url=next_url)

@admin_bp.route('/preview')
@admin_required
def preview():
    initial_path = normalize_preview_path(request.args.get('path', '/'))
    preview_pages = [{'label': 'Home', 'path': '/'}, {'label': 'Flats', 'path': '/flats'}, {'label': 'Interior', 'path': '/interior'}, {'label': 'Login', 'path': '/login'}]
    return render_template('preview.html', initial_path=initial_path, preview_pages=preview_pages)

@admin_bp.route('/approve/<item_type>/<int:id>', methods=['POST'])
@admin_required
@limiter.limit("30 per minute")
def approve_listing(item_type, id):
    item = get_listing_item(item_type, id)
    item.status = 'approved'
    db.session.commit()
    flash('Listing approved!')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/delete/<item_type>/<int:id>', methods=['POST'])
@admin_required
@limiter.limit("20 per minute")
def delete_listing(item_type, id):
    item = get_listing_item(item_type, id)
    db.session.delete(item)
    db.session.commit()
    flash('Listing deleted!')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/status/<item_type>/<int:id>', methods=['POST'])
@admin_required
@limiter.limit("60 per minute")
def update_listing_status(item_type, id):
    status = normalize_status(request.form.get('status'))
    if not status: abort(400)
    item = get_listing_item(item_type, id)
    item.status = status
    db.session.commit()
    flash('Listing status updated!', 'success')
    return redirect(request.referrer or url_for('admin.admin_dashboard'))

@admin_bp.route('/leads/<int:id>/status', methods=['POST'])
@admin_required
@limiter.limit("60 per minute")
def update_lead_status(id):
    status = normalize_lead_status(request.form.get('status'))
    if not status: abort(400)
    lead = Lead.query.get_or_404(id)
    lead.status = status
    db.session.commit()
    flash('Lead status updated!', 'success')
    return redirect(request.referrer or url_for('admin.admin_dashboard', tab='leads'))

@admin_bp.route('/leads/<int:id>/delete', methods=['POST'])
@admin_required
@limiter.limit("30 per minute")
def delete_lead(id):
    lead = Lead.query.get_or_404(id)
    db.session.delete(lead)
    db.session.commit()
    flash('Lead deleted!', 'success')
    return redirect(request.referrer or url_for('admin.admin_dashboard', tab='leads'))

@admin_bp.route('/bulk/<item_type>', methods=['POST'])
@admin_required
@limiter.limit("30 per minute")
def bulk_update_listings(item_type):
    action = request.form.get('action', '').strip().lower()
    ids = [coerce_int(value, 0) for value in request.form.getlist('ids')]
    ids = [item_id for item_id in ids if item_id > 0]
    if not ids:
        flash('Select at least one listing.', 'warning')
        return redirect(request.referrer or url_for('admin.admin_dashboard'))

    if item_type == 'flat': model = Flat; redirect_tab = 'flats'
    elif item_type == 'interior': model = InteriorService; redirect_tab = 'services'
    else: abort(404)

    query = model.query.filter(model.id.in_(ids))
    if action in LISTING_STATUSES:
        query.update({'status': action}, synchronize_session=False)
        db.session.commit()
        flash('Listings updated!', 'success')
    elif action == 'delete':
        query.delete(synchronize_session=False)
        db.session.commit()
        flash('Listings deleted!', 'success')
    else: abort(400)
    return redirect(request.referrer or url_for('admin.admin_dashboard', tab=redirect_tab))

@admin_bp.route('/leads/bulk', methods=['POST'])
@admin_required
@limiter.limit("30 per minute")
def bulk_update_leads():
    action = request.form.get('action', '').strip().lower()
    ids = [coerce_int(value, 0) for value in request.form.getlist('ids')]
    ids = [item_id for item_id in ids if item_id > 0]
    if not ids:
        flash('Select at least one lead.', 'warning')
        return redirect(request.referrer or url_for('admin.admin_dashboard', tab='leads'))

    query = Lead.query.filter(Lead.id.in_(ids))
    if action in LEAD_STATUSES:
        query.update({'status': action}, synchronize_session=False)
        db.session.commit()
        flash('Leads updated!', 'success')
    elif action == 'delete':
        query.delete(synchronize_session=False)
        db.session.commit()
        flash('Leads deleted!', 'success')
    else: abort(400)
    return redirect(request.referrer or url_for('admin.admin_dashboard', tab='leads'))

@admin_bp.route('/edit/<item_type>/<int:id>', methods=['GET', 'POST'])
@admin_required
@limiter.limit("60 per minute")
def edit_listing(item_type, id):
    item = get_listing_item(item_type, id)
    if request.method == 'POST':
        status = normalize_status(request.form.get('status'))
        if status: item.status = status

        image_file = request.files.get('image_file')
        gallery_files = request.files.getlist('image_files')
        gallery_urls = parse_image_urls(request.form.get('image_urls', ''))
        uploaded_url = save_uploaded_image(image_file)
        if image_file and image_file.filename and not uploaded_url: flash('Unsupported image type. Use PNG, JPG, or WEBP.', 'warning')
        image_url = request.form.get('image_url', '').strip()
        if uploaded_url: item.image_url = uploaded_url
        elif image_url: item.image_url = image_url

        if item_type == 'flat':
            item.title = request.form.get('title', '').strip()
            item.location = request.form.get('location', '').strip()
            item.description = request.form.get('description', '').strip()
            item.price = coerce_float(request.form.get('price'), item.price or 0)
            item.bhk = coerce_int(request.form.get('bhk'), item.bhk or 1)
            item.area_sqft = coerce_int(request.form.get('area_sqft'), item.area_sqft or 0)
            raw_video_url = request.form.get('video_url', '').strip()
            item.video_url = raw_video_url if extract_youtube_id(raw_video_url) else None
            remove_ids = request.form.getlist('remove_image_ids')
            if remove_ids: FlatImage.query.filter(FlatImage.flat_id == item.id, FlatImage.id.in_(remove_ids)).delete(synchronize_session='fetch')
            extra_urls, invalid = collect_uploaded_images(gallery_files)
            if invalid: flash('Some gallery images were not accepted. Use PNG, JPG, or WEBP.', 'warning')
            existing_count = FlatImage.query.filter_by(flat_id=item.id).count()
            remaining_slots = max(0, current_app.config['MAX_GALLERY_IMAGES'] - existing_count)
            for url in (extra_urls + gallery_urls)[:remaining_slots]:
                if url and url != item.image_url: db.session.add(FlatImage(flat=item, image_url=url))
        else:
            item.provider_name = request.form.get('provider_name', '').strip()
            item.service_type = request.form.get('service_type', '').strip()
            item.description = request.form.get('description', '').strip()
            item.portfolio_url = request.form.get('portfolio_url', '').strip()
            item.starting_price = coerce_float(request.form.get('starting_price'), item.starting_price or 0)
            remove_ids = request.form.getlist('remove_image_ids')
            if remove_ids: InteriorImage.query.filter(InteriorImage.service_id == item.id, InteriorImage.id.in_(remove_ids)).delete(synchronize_session='fetch')
            extra_urls, invalid = collect_uploaded_images(gallery_files)
            if invalid: flash('Some gallery images were not accepted. Use PNG, JPG, or WEBP.', 'warning')
            existing_count = InteriorImage.query.filter_by(service_id=item.id).count()
            remaining_slots = max(0, current_app.config['MAX_GALLERY_IMAGES'] - existing_count)
            for url in (extra_urls + gallery_urls)[:remaining_slots]:
                if url and url != item.image_url: db.session.add(InteriorImage(service=item, image_url=url))

        db.session.commit()
        flash('Listing updated successfully!', 'success')
        return redirect(url_for('admin.admin_dashboard', tab='flats' if item_type == 'flat' else 'services'))

    template = 'admin_edit_flat.html' if item_type == 'flat' else 'admin_edit_service.html'
    return render_template(template, item=item)

@admin_bp.route('/post-listing', methods=['GET', 'POST'])
@admin_required
@limiter.limit("30 per hour")
def post_listing():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        status = 'pending'
        image_file = request.files.get('image_file')
        gallery_files = request.files.getlist('image_files')
        gallery_urls = parse_image_urls(request.form.get('image_urls', ''))
        uploaded_url = save_uploaded_image(image_file)
        if image_file and image_file.filename and not uploaded_url: flash('Unsupported image type.', 'warning')

        if form_type == 'flat':
            raw_video_url = request.form.get('video_url', '').strip()
            video_url = raw_video_url if extract_youtube_id(raw_video_url) else None
            new_flat = Flat(
                title=request.form.get('title', '').strip(), location=request.form.get('location', '').strip(),
                price=coerce_float(request.form.get('price'), 0), bhk=coerce_int(request.form.get('bhk'), 1),
                area_sqft=coerce_int(request.form.get('area'), 0), description=request.form.get('description', '').strip(),
                image_url=uploaded_url or request.form.get('image_url', '').strip(), video_url=video_url, user_id=current_user.id
            )
            new_flat.status = status
            db.session.add(new_flat)
            extra_urls, invalid = collect_uploaded_images(gallery_files)
            for url in (extra_urls + gallery_urls)[:current_app.config['MAX_GALLERY_IMAGES']]:
                if url and url != new_flat.image_url: db.session.add(FlatImage(flat=new_flat, image_url=url))
        elif form_type == 'interior':
            new_service = InteriorService(
                provider_name=request.form.get('provider_name', '').strip(), service_type=request.form.get('service_type', '').strip(),
                starting_price=coerce_float(request.form.get('starting_price'), 0), description=request.form.get('description', '').strip(),
                portfolio_url=request.form.get('portfolio_url', '').strip(), image_url=uploaded_url or request.form.get('image_url', '').strip(),
                user_id=current_user.id
            )
            new_service.status = status
            db.session.add(new_service)
            extra_urls, invalid = collect_uploaded_images(gallery_files)
            for url in (extra_urls + gallery_urls)[:current_app.config['MAX_GALLERY_IMAGES']]:
                if url and url != new_service.image_url: db.session.add(InteriorImage(service=new_service, image_url=url))
        else: abort(400)
        
        db.session.commit()
        flash('Listing posted successfully!', 'success')
        return redirect(url_for('admin.admin_dashboard', tab='flats' if form_type == 'flat' else 'services'))
    return render_template('post_listing.html')

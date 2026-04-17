import os
import time
import re
import json
from urllib.parse import urlparse, parse_qs
from functools import wraps
from flask import request, redirect, url_for, abort, current_app
from flask_login import current_user
from werkzeug.utils import secure_filename
from models import db, Flat, InteriorService, Lead

YOUTUBE_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{11}$')
LISTING_STATUSES = {'pending', 'approved', 'rejected'}
LEAD_STATUSES = {'new', 'contacted', 'closed'}

def is_allowed_image(filename):
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config['ALLOWED_IMAGE_EXTENSIONS']

def get_image_type(header):
    if header.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if header.startswith(b'RIFF') and header[8:12] == b'WEBP':
        return 'webp'
    return None

def save_uploaded_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    if not is_allowed_image(file_storage.filename):
        return None
    if file_storage.mimetype and not file_storage.mimetype.startswith('image/'):
        return None
    
    try:
        from PIL import Image, ImageOps
        img = Image.open(file_storage.stream)
        img = ImageOps.exif_transpose(img)
        
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            
        max_size = 1600
        if max(img.size) > max_size:
            scale = max_size / float(max(img.size))
            new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
        upload_dir = os.path.join(current_app.static_folder, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        safe_name = secure_filename(file_storage.filename)
        timestamp = int(time.time() * 1000)
        name_root, _ = os.path.splitext(safe_name)
        filename = f"{timestamp}_{name_root}.webp"
        file_path = os.path.join(upload_dir, filename)
        
        img.save(file_path, 'WEBP', quality=80, optimize=True)
        return url_for('static', filename=f'uploads/{filename}')
        
    except Exception as e:
        print(f"Error optimizing image: {e}")
        try:
            file_storage.stream.seek(0)
            upload_dir = os.path.join(current_app.static_folder, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            safe_name = secure_filename(file_storage.filename)
            timestamp = int(time.time() * 1000)
            filename = f"{timestamp}_{safe_name}"
            file_storage.save(os.path.join(upload_dir, filename))
            return url_for('static', filename=f'uploads/{filename}')
        except:
            return None

def parse_image_urls(raw_text):
    if not raw_text:
        return []
    parts = re.split(r'[,\n\r]+', raw_text)
    return [part.strip() for part in parts if part.strip()]

def collect_uploaded_images(files):
    urls = []
    invalid = False
    for file_storage in files:
        if not file_storage or not file_storage.filename:
            continue
        uploaded = save_uploaded_image(file_storage)
        if uploaded:
            urls.append(uploaded)
        else:
            invalid = True
    return urls, invalid

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

_STATS_CACHE = {}
_redis_client = None
_redis_checked = False

def get_redis_client():
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    redis_url = os.getenv('REDIS_URL')
    if not redis_url:
        return None
    try:
        from redis import Redis
        client = Redis.from_url(redis_url, decode_responses=True)
        client.ping()
        _redis_client = client
    except Exception:
        _redis_client = None
    return _redis_client

def build_cache_key(key):
    prefix = os.getenv('CACHE_KEY_PREFIX', 'flatlandbd')
    return f'{prefix}:{key}'

def build_status_counts(model):
    from sqlalchemy import func
    rows = db.session.query(model.status, func.count(model.id)).group_by(model.status).all()
    counts = {status: total for status, total in rows}
    counts['total'] = sum(counts.values())
    return counts

def collect_admin_stats():
    flat_counts = build_status_counts(Flat)
    service_counts = build_status_counts(InteriorService)
    lead_counts = build_status_counts(Lead)
    return {
        'total_flats': flat_counts.get('total', 0),
        'pending_flats': flat_counts.get('pending', 0),
        'approved_flats': flat_counts.get('approved', 0),
        'rejected_flats': flat_counts.get('rejected', 0),
        'total_services': service_counts.get('total', 0),
        'pending_services': service_counts.get('pending', 0),
        'approved_services': service_counts.get('approved', 0),
        'rejected_services': service_counts.get('rejected', 0),
        'total_leads': lead_counts.get('total', 0),
        'new_leads': lead_counts.get('new', 0),
    }

def paginate_query(query, page, per_page):
    page = max(page, 1)
    offset = (page - 1) * per_page
    items = query.offset(offset).limit(per_page + 1).all()
    has_next = len(items) > per_page
    return items[:per_page], page > 1, has_next

def get_cached_value(key, ttl_seconds, factory):
    cache_key = build_cache_key(key)
    redis_client = get_redis_client()
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached is not None:
                return json.loads(cached)
        except Exception:
            pass

    now = time.monotonic()
    cached = _STATS_CACHE.get(key)
    if cached and cached['expires_at'] > now:
        return cached['value']
    value = factory()
    _STATS_CACHE[key] = {'value': value, 'expires_at': now + ttl_seconds}
    if redis_client:
        try:
            redis_client.setex(cache_key, ttl_seconds, json.dumps(value))
        except (TypeError, ValueError):
            pass
        except Exception:
            pass
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
            return redirect(url_for('public.login', next=safe_next_path()))
        if current_user.role != 'admin':
            abort(404)
        return f(*args, **kwargs)
    return decorated_function

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

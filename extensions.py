import os
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_compress import Compress
from flask_login import LoginManager

csrf = CSRFProtect()
compress = Compress()
login_manager = LoginManager()

rate_limit_storage_uri = os.getenv('RATELIMIT_STORAGE_URI') or os.getenv('REDIS_URL') or 'memory://'
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["2000 per day", "500 per hour"],
    storage_uri=rate_limit_storage_uri,
)

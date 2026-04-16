import os
import multiprocessing


bind = os.getenv("GUNICORN_BIND", f"0.0.0.0:{os.getenv('PORT', '8000')}")
workers = int(os.getenv("GUNICORN_WORKERS", max(multiprocessing.cpu_count() * 2 - 1, 2)))
threads = int(os.getenv("GUNICORN_THREADS", "2"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))
worker_tmp_dir = os.getenv("GUNICORN_WORKER_TMP_DIR", "/dev/shm")
accesslog = os.getenv("GUNICORN_ACCESSLOG", "-")
errorlog = os.getenv("GUNICORN_ERRORLOG", "-")
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")
capture_output = True
preload_app = os.getenv("GUNICORN_PRELOAD", "0") == "1"

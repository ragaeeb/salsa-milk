import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", "1")) or 1
threads = int(os.environ.get("WEB_THREADS", "1")) or 1
# Allow long-running Demucs jobs to finish without being killed by Gunicorn.
timeout = int(os.environ.get("WEB_TIMEOUT", "600"))
graceful_timeout = int(os.environ.get("WEB_GRACEFUL_TIMEOUT", str(timeout)))
# Temporary directory for workers to avoid issues on systems without /tmp permissions.
worker_tmp_dir_candidate = os.environ.get("WORKER_TMP_DIR", "/dev/shm")
if os.path.isdir(worker_tmp_dir_candidate):
    worker_tmp_dir = worker_tmp_dir_candidate
# Limit the maximum requests to recycle workers periodically in long-running deployments.
max_requests = int(os.environ.get("WEB_MAX_REQUESTS", "0")) or None
max_requests_jitter = int(os.environ.get("WEB_MAX_REQUESTS_JITTER", "0")) or 0

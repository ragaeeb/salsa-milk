import os


def _int_env(name: str, default: int | None, *, minimum: int | None = None, allow_none: bool = False) -> int | None:
    """Best-effort integer parsing that tolerates Render-style empty values."""

    raw = os.environ.get(name)
    if raw is None:
        return default

    raw = raw.strip()

    if allow_none and raw.lower() in {"", "none", "null"}:
        return None

    if raw == "":
        return default

    try:
        value = int(raw)
    except ValueError:
        return default

    if minimum is not None:
        return max(value, minimum)

    return value


bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = _int_env("WEB_CONCURRENCY", 1, minimum=1) or 1
threads = _int_env("WEB_THREADS", 1, minimum=1) or 1
# Allow long-running Demucs jobs to finish without being killed by Gunicorn.
timeout = _int_env("WEB_TIMEOUT", 600, minimum=1) or 600
graceful_timeout = _int_env("WEB_GRACEFUL_TIMEOUT", timeout or 600, minimum=1) or timeout or 600
# Temporary directory for workers to avoid issues on systems without /tmp permissions.
worker_tmp_dir_candidate = os.environ.get("WORKER_TMP_DIR", "/dev/shm")
if os.path.isdir(worker_tmp_dir_candidate):
    worker_tmp_dir = worker_tmp_dir_candidate
# Limit the maximum requests to recycle workers periodically in long-running deployments.
max_requests = _int_env("WEB_MAX_REQUESTS", None, allow_none=True)
if max_requests is not None and max_requests <= 0:
    max_requests = None
max_requests_jitter = _int_env("WEB_MAX_REQUESTS_JITTER", 0, minimum=0) or 0

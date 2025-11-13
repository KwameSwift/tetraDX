"""
Gunicorn configuration file for production deployment.
"""

import multiprocessing
import os

# Bind to all interfaces on port 8000
bind = "0.0.0.0:8000"

# Number of worker processes
# Formula: (2 x $num_cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Worker class - sync is default and suitable for most Django apps
worker_class = "sync"

# Maximum number of requests a worker will process before restarting
# Helps prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Timeout for worker processes (seconds)
# Increased from default 30s to handle longer-running requests
timeout = 120

# Timeout for graceful workers restart (seconds)
graceful_timeout = 30

# Timeout to keep alive connections (seconds)
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stderr
loglevel = os.getenv("LOG_LEVEL", "info")

# Access log format - shows detailed request information
# %(h) = remote address, %(l) = '-', %(u) = user name, %(t) = date/time
# %(r) = request line, %(s) = status, %(b) = response length
# %(f) = referer, %(a) = user agent, %(D) = request time in microseconds
# %(M) = request time in milliseconds
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(M)sms'
)

# Process naming
proc_name = "tetradx"

# Preload application code before worker processes are forked
# This can save RAM and speed up boot times
preload_app = True

# Worker restart on code changes (useful for development)
reload = os.getenv("ENVIRONMENT") in ["development", "dev", "local"]

# Maximum number of pending connections
backlog = 2048

# Request Logging Configuration

## What Was Added

### ✅ Gunicorn Access Logging
Added detailed access log format that shows:
- Client IP address
- Request timestamp
- HTTP method and path
- Response status code
- Response size
- User agent
- **Request processing time in milliseconds**

### ✅ Django Request Logging
Configured comprehensive logging for:
- All Django requests (`django.request`)
- Server events (`django.server`)
- Application-specific logs (authentication, medics, utilities)
- Optional database query logging

## How to View Request Logs

### In Docker (Production)

**View live logs:**
```bash
docker logs -f tetraDX-backend
```

**View last 100 lines:**
```bash
docker logs --tail 100 tetraDX-backend
```

**Filter for specific requests:**
```bash
# Only show GET requests
docker logs -f tetraDX-backend | grep "GET"

# Only show errors (4xx, 5xx)
docker logs -f tetraDX-backend | grep -E "\" [45][0-9]{2} "

# Show slow requests (>1000ms)
docker logs -f tetraDX-backend | grep -E "[0-9]{4,}ms"
```

### Log Format Examples

**Gunicorn access log:**
```
172.18.0.1 - - [13/Nov/2025:10:30:45 +0000] "GET /api/medics/referrals/practitioner HTTP/1.1" 200 1234 "-" "Mozilla/5.0" 145ms
```

**Django request log:**
```
[INFO] 2025-11-13 10:30:45 django.request log GET /api/medics/referrals/practitioner
```

## Adjusting Log Levels

### Temporary (Current Container)

```bash
# More verbose - see all requests and debug info
docker-compose up -d -e DJANGO_LOG_LEVEL=DEBUG -e LOG_LEVEL=debug

# Less verbose - only warnings and errors
docker-compose up -d -e DJANGO_LOG_LEVEL=WARNING -e LOG_LEVEL=warning
```

### Permanent (Environment File)

Create/edit `.env` file:
```env
ENVIRONMENT=production
LOG_LEVEL=info
DJANGO_LOG_LEVEL=INFO
DB_LOG_LEVEL=WARNING  # Set to DEBUG to see SQL queries
```

## Log Levels Explained

| Level | What You'll See |
|-------|----------------|
| DEBUG | Everything: requests, SQL queries, debug messages |
| INFO | Normal operations: requests, responses, status changes |
| WARNING | Potential issues: deprecated features, unusual conditions |
| ERROR | Errors that should be investigated |
| CRITICAL | Severe errors that need immediate attention |

## Debugging Database Performance

To see SQL queries (useful for debugging N+1 issues):

```bash
# In docker-compose.yml or .env
DB_LOG_LEVEL=DEBUG
```

Then restart:
```bash
docker-compose restart
docker logs -f tetraDX-backend | grep "SELECT"
```

## Production Best Practices

### Recommended Settings:
```env
ENVIRONMENT=production
LOG_LEVEL=info           # Shows access logs
DJANGO_LOG_LEVEL=INFO    # Shows Django requests
DB_LOG_LEVEL=WARNING     # Hides SQL queries (performance)
```

### For Debugging Issues:
```env
ENVIRONMENT=production
LOG_LEVEL=debug
DJANGO_LOG_LEVEL=DEBUG
DB_LOG_LEVEL=DEBUG       # Shows all SQL queries
```

⚠️ **Note:** DEBUG level logging can impact performance and expose sensitive data. Use only when debugging.

## Log Analysis

### Find Slow Requests
```bash
# Find requests taking more than 500ms
docker logs tetraDX-backend | grep -E "[5-9][0-9]{2,}ms|[0-9]{4,}ms"
```

### Count Requests by Status Code
```bash
docker logs tetraDX-backend | grep -oE "\" [0-9]{3} " | sort | uniq -c | sort -rn
```

### Find Error Responses
```bash
docker logs tetraDX-backend | grep -E "\" [45][0-9]{2} "
```

### Monitor Real-time with Color
```bash
docker logs -f tetraDX-backend | grep --color=auto -E "GET|POST|PUT|DELETE|PATCH"
```

## Testing the Logging

After deploying, test with:

```bash
# Start watching logs
docker logs -f tetraDX-backend

# In another terminal, make a test request
curl http://localhost:8000/api/medics/facilities/

# You should see in logs:
# [Gunicorn] IP address, timestamp, "GET /api/medics/facilities/ HTTP/1.1" 200 ... Xms
# [Django] [INFO] timestamp django.request GET /api/medics/facilities/
```

## Troubleshooting

### Not seeing any logs?
```bash
# Check if container is running
docker ps

# Check container logs directly
docker logs tetraDX-backend

# Restart container
docker-compose restart
```

### Logs too verbose?
Reduce to WARNING level:
```bash
docker-compose down
# Update .env or docker-compose.yml
docker-compose up -d
```

### Want to save logs to file?
```bash
# Save current logs
docker logs tetraDX-backend > app_logs_$(date +%Y%m%d).log

# Continuously save to file
docker logs -f tetraDX-backend >> app_logs.log
```

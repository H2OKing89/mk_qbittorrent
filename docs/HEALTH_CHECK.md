# Health Check API

The application now includes a comprehensive health check endpoint for monitoring and diagnostics.

## Endpoint

```
GET /api/health
```

## Response Format

```json
{
  "status": "healthy",
  "timestamp": 1756438472.4680638,
  "checks": {
    "managers": {
      "config_manager": true,
      "secure_config_manager": true,
      "torrent_manager": true,
      "settings_storage": true
    },
    "qbittorrent": {
      "connected": true,
      "message": "Connected to qBittorrent v5.1.2 (Web API v2.11.4)"
    },
    "configuration": {
      "accessible": true,
      "message": "Config loaded successfully"
    },
    "filesystem": {
      "accessible": true,
      "message": "File operations working"
    },
    "system": {
      "memory_mb": "psutil not available",
      "cpu_percent": "psutil not available"
    }
  },
  "response_time_ms": 108.54
}
```

## Health Checks Performed

1. **Manager Initialization**: Verifies all core managers are properly initialized
2. **qBittorrent Connection**: Tests actual connectivity to qBittorrent API
3. **Configuration Access**: Ensures configuration can be loaded and accessed
4. **Filesystem Operations**: Tests basic file read/write operations
5. **System Resources**: Monitors memory and CPU usage (requires psutil)

## Status Values

- `healthy`: All checks passed
- `degraded`: Some non-critical checks failed
- `critical`: Critical functionality is impaired

## Usage Examples

### Docker Health Check
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8094/api/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Monitoring Script
```bash
# Use the included health monitor
./health_monitor.sh http://localhost:8094/api/health 30

# Or check manually
curl -s http://localhost:8094/api/health | jq '.status'
```

### Load Balancer Health Check
Configure your load balancer to check `/api/health` with:
- Expected HTTP status: 200
- Expected response contains: `"status": "healthy"`

## Response Time Monitoring

The `response_time_ms` field helps monitor API performance. Typical healthy response times are under 100ms.

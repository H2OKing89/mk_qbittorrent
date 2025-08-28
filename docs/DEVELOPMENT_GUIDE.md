# Development Guide: qBittorrent API Integration

This guide outlines best practices for working with the qBittorrent API in our torrent creation application, based on the official `qbittorrent-api` documentation.

## Client Configuration Best Practices

### 1. Production-Ready Client Setup

Our `TorrentManager` now implements a hardened client configuration:

```python
client = qbittorrentapi.Client(
    host=qbit_url,
    username=username,
    password=password,
    VERIFY_WEBUI_CERTIFICATE=verify_tls,
    # Timeouts prevent hanging
    REQUESTS_ARGS={
        "timeout": (connection_timeout, read_timeout),  # (connect, read)
    },
    # Connection pooling for performance
    HTTPADAPTER_ARGS={
        "pool_connections": pool_connections,
        "pool_maxsize": pool_maxsize,
    },
    # Strict error handling
    RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True,
    RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS=False,
    # Reduce debug noise
    DISABLE_LOGGING_DEBUG_OUTPUT=True,
)
```

### 2. Configuration Parameters

These settings are now configurable in `config.yaml`:

```yaml
qbittorrent:
  # Connection settings
  host: "localhost"
  port: 8080
  use_https: false
  base_path: ""  # For reverse proxy setups
  verify_tls: true
  
  # Performance settings
  connection_timeout: 10.0  # seconds
  read_timeout: 30.0       # seconds
  pool_connections: 10     # HTTP pool size
  pool_maxsize: 10        # HTTP pool max size
```

## Exception Handling

### Specific Exception Types

We now catch and handle specific qBittorrent API exceptions:

```python
try:
    client.auth_log_in()
except qba_exc.LoginFailed:
    # Bad credentials
except qba_exc.Forbidden403Error:
    # IP banned due to failed auth attempts
except qba_exc.Unauthorized401Error:
    # Session expired or unauthorized
except qba_exc.APIConnectionError:
    # Network/connectivity issues
except qba_exc.UnsupportedQbittorrentVersion:
    # Version compatibility issues
```

### Torrent Creation Specific Exceptions

```python
try:
    task = client.torrentcreator.add_task(...)
except qba_exc.Conflict409Error:
    # Too many concurrent tasks - retry later
except qba_exc.NotFound404Error:
    # Source path not accessible to qBittorrent
```

## Resource Management

### Context Manager Pattern

Our `TorrentManager` now supports async context manager for proper cleanup:

```python
async with TorrentManager(config) as tm:
    result = await tm.create_torrent(source_path)
    # Automatic cleanup on exit
```

### Session Cleanup

Always clean up qBittorrent sessions to prevent memory bloat:

```python
async def cleanup(self):
    if self._qbit_client:
        try:
            self._qbit_client.auth_log_out()
        except Exception as e:
            # Log but don't fail on cleanup errors
        finally:
            self._qbit_client = None
```

## Task Management

### Task Lifecycle

1. **Create Task**: Use `add_task()` with comprehensive parameters
2. **Poll Status**: Check task status until completion
3. **Handle Results**: Retrieve torrent file or handle errors
4. **Cleanup**: Always delete completed/failed tasks

### Task Cleanup Best Practices

```python
try:
    task.delete()
    print(f"🧹 Cleaned up task {task_id}")
except Exception as cleanup_error:
    print(f"Warning: Could not cleanup task {task_id}: {cleanup_error}")
    # Don't fail the main operation due to cleanup issues
```

## API Features We Utilize

### Torrent Creator API (v5.0.0+)

Full parameter support:
- `source_path`: File/directory to create torrent from
- `format`: v1, v2, or hybrid
- `start_seeding`: Auto-add to qBittorrent for seeding
- `is_private`: Private torrent flag
- `piece_size`: Custom piece size (optional)
- `comment`: Embedded comment
- `trackers`: Tracker URLs
- `url_seeds`: Web seeds for HTTP/HTTPS mirrors
- `source`: Content source identifier

### Connection Features

- Automatic re-authentication on session expiry
- Support for HTTPS with custom certificate verification
- Reverse proxy support via `base_path`
- Connection pooling for performance

## Docker Integration

### Path Mapping

Our Docker path mapper handles qBittorrent container paths:

```python
# Host path: /mnt/user/media/Movie.mkv
# Container path: /data/media/Movie.mkv
container_path = self._path_mapper.host_to_container(host_path)
```

### Configuration

```yaml
qbittorrent:
  docker_path_mapping:
    "/mnt/user/data": "/data"
    "/mnt/user/downloads": "/downloads"
```

## Error Recovery Patterns

### Graceful Degradation

If advanced parameters fail, try minimal parameters:

```python
try:
    task = client.torrentcreator.add_task(
        source_path=path,
        format=format,
        # ... all parameters
    )
except Exception:
    # Fallback to minimal parameters
    task = client.torrentcreator.add_task(source_path=path)
```

### Timeout Handling

```python
max_wait_time = 300  # 5 minutes
poll_interval = 2    # 2 seconds
elapsed_time = 0

while elapsed_time < max_wait_time:
    await asyncio.sleep(poll_interval)
    elapsed_time += poll_interval
    
    status = task.status()
    if status.status == TaskStatus.FINISHED:
        break
    elif status.status == TaskStatus.FAILED:
        break

if elapsed_time >= max_wait_time:
    # Handle timeout
```

## Performance Considerations

### Connection Pooling

Use appropriate pool sizes based on expected load:

```python
HTTPADAPTER_ARGS={
    "pool_connections": 10,  # Number of connection pools
    "pool_maxsize": 10,     # Max connections per pool
}
```

### Timeouts

Set reasonable timeouts to prevent hanging:

```python
REQUESTS_ARGS={
    "timeout": (10.0, 30.0),  # (connect_timeout, read_timeout)
}
```

### Task Limits

qBittorrent has limits on concurrent torrent creation tasks. Handle `Conflict409Error` appropriately.

## Security Best Practices

### TLS Verification

Always verify TLS certificates in production:

```python
VERIFY_WEBUI_CERTIFICATE=True  # Default, never disable in production
```

### Credential Management

Use our credential manager for secure storage:

```python
# Store credentials securely
credential_manager.store_credential("QBIT_USERNAME", username)
credential_manager.store_credential("QBIT_PASSWORD", password)

# Retrieve for use
username = credential_manager.get_credential("QBIT_USERNAME")
password = credential_manager.get_credential("QBIT_PASSWORD")
```

### Environment Variable Fallback

For development/testing, support `.env` file fallback:

```bash
# config/.env
QBIT_USERNAME=admin
QBIT_PASSWORD=adminpass
```

## Troubleshooting

### Common Issues

1. **IP Banned**: Wait or restart qBittorrent after failed auth attempts
2. **Task Conflicts**: Too many concurrent tasks - implement queuing
3. **Path Issues**: Ensure Docker path mapping is correct
4. **Version Issues**: Torrent Creator API requires qBittorrent v5.0.0+

### Logging

Enable detailed logging for troubleshooting:

```python
# Temporarily enable for debugging
DISABLE_LOGGING_DEBUG_OUTPUT=False
VERBOSE_RESPONSE_LOGGING=True
```

## References

- [qBittorrent API Documentation](docs/qBittorrent_api_create.md)
- [Client Configuration Guide](docs/qBittorrent_api_client.md)
- [Authentication Reference](docs/qBittorrent_api_authentication.md)
- [qbittorrent-api Python Package](docs/qbittorrent-api.py.md)

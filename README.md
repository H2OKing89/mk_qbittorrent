# Easy Torrent Creator 🚀

A modular, user-friendly application for creating torrents using qBittorrent API integration.

## Features

- **🌐 Web Interface** - Modern, responsive web UI perfect for headless systems
- **⌨️ Command Line** - Full CLI support for automation
- **🔒 Secure Configuration** - Environment variable support for sensitive data
- **📁 Smart Folder Browser** - Intuitive file/folder selection
- **⚡ Real-time Validation** - Instant feedback on folder selection
- **🎯 Novice-Friendly** - Designed for ease of use

## Quick Start

### Web Interface (Recommended for headless systems)

```bash
# Install dependencies
pip install fastapi uvicorn jinja2 python-multipart

# Start web server
python main.py --web

# Open browser to http://localhost:8094
```

### Command Line

```bash
# Create torrent from command line
python main.py --cli /path/to/folder --output ./torrents --private
```

## Configuration

### Environment Variables (Recommended)

Create a `.env` file or set environment variables:

```bash
# Tracker URL with passkey (keep this secret!)
export TRACKER="https://tracker.example.com/announce?passkey=your_secret_key"

# qBittorrent password (optional)
export QB_PASSWORD="your_qbit_password"
```

### Configuration File

Edit `config/config.yaml`:

```yaml
qbittorrent:
  host: localhost
  port: 8080
  username: admin
  password: ""  # Use ${QB_PASSWORD} for env var

trackers:
  - "${TRACKER}"  # References environment variable

default_output_dir: "./torrents"

torrent_creation:
  piece_size: 0  # Auto
  private: true
  start_seeding: false
  optimize_alignment: true
```

## Project Structure

```
├── src/
│   ├── core/               # Core functionality
│   │   ├── config_manager.py
│   │   └── torrent_manager.py
│   ├── web/                # Web interface
│   │   ├── app.py
│   │   ├── templates/
│   │   └── static/
│   ├── cli/                # Command line interface
│   └── utils/              # Shared utilities
├── config/
│   └── config.yaml
└── main.py                 # Entry point
```

## Web Interface Features

- **📂 Folder Browser**: Navigate filesystem with visual feedback
- **📊 Folder Analysis**: Real-time size/file count validation
- **⚙️ Configuration**: Web-based settings management
- **🔗 Connection Testing**: Verify qBittorrent connectivity
- **📱 Responsive Design**: Works on desktop and mobile
- **🎨 Modern UI**: Clean, intuitive interface with Alpine.js

## API Endpoints

The web interface provides a full REST API:

- `GET /` - Main interface
- `GET /config` - Configuration page
- `GET /api/folders?path=` - Browse folders
- `GET /api/folder-info?path=` - Get folder details
- `POST /api/create-torrent` - Create torrent
- `POST /api/test-connection` - Test qBittorrent connection
- `GET /api/config` - Get configuration
- `POST /api/save-config` - Save configuration
- `GET /api/env-vars` - Check environment variables

## Advanced Usage

### Custom Configuration File

```bash
python main.py --config-file /custom/path/config.yaml --web
```

### Different Web Server Port

```bash
python main.py --web --host 0.0.0.0 --port 9000
```

### Verbose Logging

```bash
python main.py --verbose --web
```

## Security Best Practices

1. **Use Environment Variables** for sensitive data (tracker passkeys, passwords)
2. **Restrict Web Access** - Use firewall rules for web interface
3. **Regular Updates** - Keep qBittorrent and dependencies updated
4. **Strong Passwords** - Use secure qBittorrent credentials

## Troubleshooting

### "Web mode not available" Error
```bash
# Install web dependencies
pip install fastapi uvicorn jinja2 python-multipart
```

### Connection Issues
1. Check qBittorrent is running
2. Verify host/port in configuration
3. Check credentials
4. Use the "Test Connection" feature

## Development

### Requirements
- Python 3.8+
- qBittorrent with Web UI enabled
- Dependencies listed in `requirements.txt`

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is designed to be user-friendly and modular. Feel free to adapt it to your needs!

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review configuration settings
3. Test connection to qBittorrent
4. Check logs for error messages

---

**Happy torrenting! 🌱**

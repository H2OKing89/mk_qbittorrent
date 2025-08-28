#!/bin/bash
# Easy Torrent Creator startup script

echo "🚀 Easy Torrent Creator"
echo "======================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found"
    echo "Please install Python 3.8 or later"
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."

python3 -c "import tkinter" 2>/dev/null || {
    echo "⚠️  tkinter not found - GUI mode may not work"
    echo "Install tkinter with: sudo apt-get install python3-tk (Ubuntu/Debian)"
}

python3 -c "import qbittorrentapi" 2>/dev/null || {
    echo "❌ qbittorrent-api not found"
    echo "Install with: pip install qbittorrent-api"
    exit 1
}

python3 -c "import rich" 2>/dev/null || {
    echo "⚠️  rich not found - progress display may be limited"
    echo "Install with: pip install rich"
}

python3 -c "import yaml" 2>/dev/null || {
    echo "⚠️  PyYAML not found - config file support may be limited"
    echo "Install with: pip install PyYAML"
}

echo "✅ Dependencies check complete"
echo ""

# Determine mode
if [ "$1" = "--cli" ]; then
    echo "🖥️  Starting CLI mode..."
    python3 main.py "$@"
elif [ "$1" = "--config" ]; then
    echo "⚙️  Opening configuration..."
    python3 main.py --config
else
    echo "🖼️  Starting GUI mode..."
    echo "Use --help for CLI options"
    python3 main.py "$@"
fi

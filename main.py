#!/usr/bin/env python3
"""
Torrent Creator - Easy to use torrent creation application
Using qBittorrent API for seamless torrent creation and management

Main entry point for the application - Headless/Web-focused version
"""
import sys
import asyncio
import argparse
from pathlib import Path

# Add the current directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.cli.commands import CLIHandler
from src.core.config_manager import ConfigManager
from src.utils.logging_setup import setup_logging


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Easy Torrent Creator - Create torrents with qBittorrent (Headless/Web-focused)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Start web interface (default)
  %(prog)s --cli /path/to/folder     # CLI mode - create torrent from folder
  %(prog)s --web                     # Explicitly start web interface
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--web', 
        action='store_true', 
        help='Start web interface (default)'
    )
    mode_group.add_argument(
        '--cli', 
        metavar='PATH',
        help='CLI mode - create torrent from specified path'
    )
    
    # Web mode options
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Web server host (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8094,
        help='Web server port (default: 8094)'
    )
    
    # CLI options
    parser.add_argument(
        '--output', '-o',
        metavar='DIR',
        help='Output directory for torrent files (CLI mode)'
    )
    parser.add_argument(
        '--private',
        action='store_true',
        help='Create private torrent (CLI mode)'
    )
    parser.add_argument(
        '--start-seeding',
        action='store_true',
        help='Start seeding after creation (CLI mode)'
    )
    
    # Global options
    parser.add_argument(
        '--config-file',
        default='config/config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


async def main():
    """Main application entry point"""
    args = parse_arguments()
    
    # Setup logging
    setup_logging(verbose=args.verbose)
    
    # Load configuration
    config_manager = ConfigManager(args.config_file)
    
    try:
        if args.cli:
            # CLI Mode
            cli_handler = CLIHandler(config_manager)
            await cli_handler.create_torrent(
                source_path=args.cli,
                output_dir=args.output,
                private=args.private,
                start_seeding=args.start_seeding
            )
        else:
            # Default to web mode (no GUI)
            print("❌ No mode specified. Starting web interface...")
            print("💡 Use --cli for command line mode")
            print("💡 Use --web to explicitly start web interface")
            
            # Start web mode
            import uvicorn
            config = config_manager.get_config()
            
            host = args.host if args.host != '0.0.0.0' else config.web_server.host
            port = args.port if args.port != 8094 else config.web_server.port
            
            print(f"🚀 Starting web server on http://{host}:{port}")
            print("💡 Open your browser and navigate to the URL above")
            print("Press Ctrl+C to stop the server")
            
            uvicorn.run(
                "src.web.app:app",
                host=host,
                port=port,
                reload=False,
                access_log=True
            )
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if sys.platform == "win32":
        # Windows specific event loop policy
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    args = parse_arguments()
    
    # Handle web mode specially since uvicorn manages its own event loop
    if args.web or (not args.cli):
        # Web mode (explicit or default)
        try:
            import uvicorn
            
            setup_logging(verbose=args.verbose)
            config_manager = ConfigManager(args.config_file)
            config = config_manager.get_config()
            
            # Use config values, but allow command line overrides
            host = args.host if args.host != '0.0.0.0' else config.web_server.host
            port = args.port if args.port != 8094 else config.web_server.port
            
            print(f"🚀 Starting web server on http://{host}:{port}")
            print("💡 Open your browser and navigate to the URL above")
            print("Press Ctrl+C to stop the server")
            
            uvicorn.run(
                "src.web.app:app",
                host=host,
                port=port,
                reload=False,
                access_log=True
            )
        except ImportError as e:
            print(f"❌ Web mode not available: {e}")
            print("💡 Install web dependencies: pip install fastapi uvicorn jinja2")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nWeb server stopped")
        except Exception as e:
            print(f"Error starting web server: {e}")
            sys.exit(1)
    else:
        # CLI mode - use asyncio
        asyncio.run(main())

#!/usr/bin/env python3
"""
Torrent Creator - Easy to use torrent creation application
Using qBittorrent API for seamless torrent creation and management

Main entry point for the application
"""
import sys
import asyncio
import argparse
from pathlib import Path

# Add the current directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.gui.main_window import TorrentCreatorApp
from src.cli.commands import CLIHandler
from src.core.config_manager import ConfigManager
from src.utils.logging_setup import setup_logging


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Easy Torrent Creator - Create torrents with qBittorrent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Start GUI mode
  %(prog)s --cli /path/to/folder     # CLI mode - create torrent from folder
  %(prog)s --gui                     # Explicitly start GUI mode
  %(prog)s --config                  # Open configuration GUI
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--gui', 
        action='store_true', 
        help='Start GUI mode (default)'
    )
    mode_group.add_argument(
        '--cli', 
        metavar='PATH',
        help='CLI mode - create torrent from specified path'
    )
    mode_group.add_argument(
        '--web', 
        action='store_true',
        help='Start web interface mode'
    )
    mode_group.add_argument(
        '--config', 
        action='store_true',
        help='Open configuration GUI'
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
    
    # Handle web mode separately since it manages its own event loop
    if args.web:
        try:
            import uvicorn
            from src.core.config_manager import ConfigManager
            
            # Load configuration for web server settings
            config_manager = ConfigManager()
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
            return
        except ImportError as e:
            print(f"❌ Web mode not available: {e}")
            print("💡 Install web dependencies: pip install fastapi uvicorn jinja2")
            sys.exit(1)
    
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
        
        elif args.config:
            # Configuration GUI
            from src.gui.config_window import ConfigWindow
            app = ConfigWindow(config_manager)
            app.run()
        
        else:
            # GUI Mode (default)
            try:
                app = TorrentCreatorApp(config_manager)
                await app.run()
            except Exception as e:
                if "tkinter" in str(e).lower():
                    print("❌ GUI mode not available (tkinter not found)")
                    print("💡 For headless systems, use: python main.py --web")
                    sys.exit(1)
                raise
            
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
    
    # Parse args first to check if web mode
    args = parse_arguments()
    
    if args.web:
        # Web mode - run directly without asyncio.run
        try:
            import uvicorn
            from src.utils.logging_setup import setup_logging
            from src.core.config_manager import ConfigManager
            
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
        # All other modes use async
        asyncio.run(main())

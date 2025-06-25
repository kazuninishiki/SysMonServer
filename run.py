#!/usr/bin/env python3
"""
System Monitor Dashboard - Quick Launcher
Simple script to start the system monitor server with options
"""

import sys
import argparse
import webbrowser
import time
from main import app, socketio, monitor, logger

def main():
    parser = argparse.ArgumentParser(description='System Monitor Dashboard Server')
    parser.add_argument('--port', '-p', type=int, default=9876, help='Server port (default: 9876)')
    parser.add_argument('--host', default='0.0.0.0', help='Server host (default: 0.0.0.0)')
    parser.add_argument('--interval', '-i', type=int, default=1000, help='Update interval in ms (default: 1000)')
    parser.add_argument('--no-browser', action='store_true', help='Don\'t open browser automatically')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Set update interval
    monitor.update_interval = args.interval
    
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                   System Monitor Dashboard                    ║
║                                                               ║
║  Server starting on http://{args.host}:{args.port:<5}                       ║
║  Update interval: {args.interval}ms                                    ║
║                                                               ║
║  Press Ctrl+C to stop the server                             ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Open browser automatically unless disabled
    if not args.no_browser:
        def open_browser():
            time.sleep(1.5)  # Wait for server to start
            webbrowser.open(f'http://localhost:{args.port}')
        
        import threading
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
    
    try:
        # Start background stats updater
        from main import background_stats_updater
        import threading
        stats_thread = threading.Thread(target=background_stats_updater, daemon=True)
        stats_thread.start()
        
        # Start server
        socketio.run(
            app, 
            host=args.host, 
            port=args.port, 
            debug=args.debug,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
        monitor.running = False
    except Exception as e:
        logger.error(f"Server startup failed {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()

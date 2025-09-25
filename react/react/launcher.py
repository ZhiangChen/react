#!/usr/bin/env python3
"""
REACT Ground Control Station Launcher
Starts the tile server and main application
"""

import subprocess
import sys
import time
import threading
import signal
import os
from pathlib import Path

class REACTLauncher:
    def __init__(self):
        self.tile_server_process = None
        self.main_app_process = None
        self.running = True
        
    def start_tile_server(self):
        """Start the tile server in background"""
        try:
            print("Starting tile server...")
            # Get the directory where launcher.py is located
            script_dir = Path(__file__).parent
            tile_server_path = script_dir / "maps" / "tile_server.py"
            
            # Use py -3.12 to ensure correct Python version
            self.tile_server_process = subprocess.Popen([
                sys.executable, str(tile_server_path)
            ], 
            cwd=str(script_dir),  # Set working directory to project root
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            print("Tile server started (PID:", self.tile_server_process.pid, ")")
            return True
        except Exception as e:
            print(f"Failed to start tile server: {e}")
            return False
    
    def start_main_app(self):
        """Start the main REACT application"""
        try:
            print("Starting REACT application...")
            # Wait a moment for tile server to initialize
            time.sleep(2)
            
            # Get the directory where launcher.py is located
            script_dir = Path(__file__).parent
            main_app_path = script_dir / "main.py"
            
            self.main_app_process = subprocess.Popen([
                sys.executable, str(main_app_path)
            ], 
            cwd=str(script_dir)  # Set working directory to project root
            )
            print("REACT application started (PID:", self.main_app_process.pid, ")")
            return True
        except Exception as e:
            print(f"Failed to start main application: {e}")
            return False
    
    def stop_processes(self):
        """Stop all processes"""
        print("\nShutting down REACT...")
        self.running = False
        
        if self.main_app_process:
            print("Stopping main application...")
            self.main_app_process.terminate()
            try:
                self.main_app_process.wait(timeout=5)
                print("Main application stopped")
            except subprocess.TimeoutExpired:
                print("Force killing main application...")
                self.main_app_process.kill()
        
        if self.tile_server_process:
            print("Stopping tile server...")
            self.tile_server_process.terminate()
            try:
                self.tile_server_process.wait(timeout=5)
                print("Tile server stopped")
            except subprocess.TimeoutExpired:
                print("Force killing tile server...")
                self.tile_server_process.kill()
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        self.stop_processes()
        sys.exit(0)
    
    def monitor_processes(self):
        """Monitor running processes"""
        while self.running:
            time.sleep(1)
            
            # Check if main app is still running
            if self.main_app_process and self.main_app_process.poll() is not None:
                print("Main application exited")
                self.running = False
                break
    
    def run(self):
        """Main launcher function"""
        print("=" * 50)
        print("REACT Ground Control Station Launcher")
        print("=" * 50)
        
        # Set up signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Start tile server
        if not self.start_tile_server():
            print("Failed to start tile server, exiting...")
            return 1
        
        # Start main application
        if not self.start_main_app():
            print("Failed to start main application, stopping tile server...")
            self.stop_processes()
            return 1
        
        print("\n" + "=" * 50)
        print("REACT is running!")
        print("- Tile server: http://127.0.0.1:8081")
        print("- Main application: Running")
        print("Press Ctrl+C to stop all services")
        print("=" * 50)
        
        # Monitor processes
        try:
            self.monitor_processes()
        except KeyboardInterrupt:
            pass
        
        # Clean shutdown
        self.stop_processes()
        return 0

def install_dependencies():
    """Install required dependencies"""
    print("Installing tile server dependencies...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "fastapi", "uvicorn", "aiohttp", "aiofiles"
        ])
        print("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("Failed to install dependencies")
        return False

def preload_tiles():
    """Pre-load tiles for a specific region"""
    if len(sys.argv) < 7:
        print("Usage: python launcher.py preload <lat_min> <lat_max> <lon_min> <lon_max> <zoom1> [zoom2] ...")
        return 1
    
    lat_min = float(sys.argv[2])
    lat_max = float(sys.argv[3]) 
    lon_min = float(sys.argv[4])
    lon_max = float(sys.argv[5])
    zoom_levels = [int(z) for z in sys.argv[6:]]
    
    print(f"Pre-loading tiles for region: {lat_min},{lon_min} to {lat_max},{lon_max}")
    print(f"Zoom levels: {zoom_levels}")
    
    try:
        script_dir = Path(__file__).parent
        tile_server_path = script_dir / "maps" / "tile_server.py"
        result = subprocess.run([
            sys.executable, str(tile_server_path), "preload", "satellite",
            str(lat_min), str(lat_max), str(lon_min), str(lon_max)
        ] + [str(z) for z in zoom_levels], cwd=str(script_dir))
        return result.returncode
    except Exception as e:
        print(f"Error pre-loading tiles: {e}")
        return 1

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "install":
            sys.exit(0 if install_dependencies() else 1)
        elif sys.argv[1] == "preload":
            sys.exit(preload_tiles())
        elif sys.argv[1] == "server-only":
            # Run only the tile server
            try:
                script_dir = Path(__file__).parent
                tile_server_path = script_dir / "maps" / "tile_server.py"
                subprocess.run([sys.executable, str(tile_server_path)], cwd=str(script_dir))
            except KeyboardInterrupt:
                pass
            sys.exit(0)
    
    # Normal startup
    launcher = REACTLauncher()
    sys.exit(launcher.run())
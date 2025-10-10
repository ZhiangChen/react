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
import math
import yaml
from pathlib import Path
import urllib.request

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
            
            # Use the same Python interpreter that's running this script
            self.tile_server_process = subprocess.Popen([
                sys.executable, str(tile_server_path)
            ], 
            cwd=str(script_dir)  # Set working directory to project root
            )
            print("Tile server started (PID:", self.tile_server_process.pid, ")")
            return True
        except Exception as e:
            print(f"Failed to start tile server: {e}")
            return False
    
    def wait_for_tile_server(self, timeout=30):
        """Wait for tile server to be ready"""
        print("Waiting for tile server to be ready...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with urllib.request.urlopen("http://127.0.0.1:8081/api/info", timeout=2) as response:
                    if response.status == 200:
                        print("Tile server is ready!")
                        return True
            except:
                pass
            time.sleep(1)
        print("Timeout waiting for tile server")
        return False
    
    def start_main_app(self):
        """Start the main REACT application"""
        try:
            print("Starting REACT application...")
            # Wait for tile server to be ready
            if not self.wait_for_tile_server():
                print("Tile server failed to start properly")
                return False
            
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
    
    def preload_default_area(self):
        """Preload map tiles around the default position from config"""
        try:
            print("\nPreloading map tiles for default area...")
            config_path = Path(__file__).parent / "config.yaml"
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            default_pos = config.get('default_home_position', {})
            if not default_pos:
                print("No default position found in config.yaml, skipping tile preload")
                return True

            lat = default_pos.get('latitude')
            lon = default_pos.get('longitude')
            zoom = default_pos.get('zoom', 12)
            
            if lat is None or lon is None:
                print("Invalid default position in config.yaml, skipping tile preload")
                return True
                
            # Calculate a bounding box around the default position (roughly 10km radius)
            lat_offset = 0.02  # About 11km at equator
            lon_offset = 0.02 / math.cos(math.radians(lat))  # Adjust for latitude
            
            # Preload tiles for zoom levels around default
            min_zoom = max(1, zoom -1)  # 1 levels out
            max_zoom = min(18, zoom + 1)  # 1 levels in

            print(f"Default position: {lat:.6f}, {lon:.6f}, zoom {zoom}")
            print(f"Preloading area: {lat-lat_offset:.6f},{lon-lon_offset:.6f} to {lat+lat_offset:.6f},{lon+lon_offset:.6f}")
            print(f"Zoom levels: {min_zoom} to {max_zoom}")
            
            script_dir = Path(__file__).parent
            tile_server_path = script_dir / "maps" / "tile_server.py"
            
            # Run preload command
            subprocess.run([
                sys.executable, str(tile_server_path), "preload", "satellite",
                str(lat-lat_offset), str(lat+lat_offset), 
                str(lon-lon_offset), str(lon+lon_offset),
                *[str(z) for z in range(min_zoom, max_zoom + 1)]
            ], check=True, cwd=str(script_dir))
            
            print("✓ Successfully preloaded map tiles for default area")
            return True
            
        except Exception as e:
            print(f"Warning: Failed to preload default area tiles: {e}")
            return True  # Continue anyway

    def run(self):
        """Main launcher function"""
        print("=" * 50)
        print("REACT Ground Control Station Launcher")
        print("=" * 50)
        
        # Set up signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Install dependencies first
        print("Installing dependencies...")
        if not install_dependencies():
            print("Failed to install dependencies, exiting...")
            return 1
        
        # Start tile server (will automatically preload tiles based on config)
        if not self.start_tile_server():
            print("Failed to start tile server, exiting...")
            return 1
        
        # Wait for tile server to be ready
        if not self.wait_for_tile_server():
            print("Tile server failed to become ready, exiting...")
            self.stop_processes()
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
            "fastapi", "uvicorn", "aiohttp", "aiofiles", "pyyaml"
        ])
        print("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("Failed to install dependencies")
        return False

# Removed preload_tiles function as it's now handled automatically by tile_server.py

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "install":
            sys.exit(0 if install_dependencies() else 1)
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
#!/usr/bin/env python3
"""
REACT Ground Control Station Launcher
Starts the tile server and main application
"""

# Set Qt Quick Controls style BEFORE any Qt imports
# This ensures rectangular (non-rounded) UI elements
import os
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Fusion"  # Fusion style provides rectangular dialogs and buttons

import subprocess
import sys
import time
import threading
import signal
import math
import yaml
import logging
from pathlib import Path
import urllib.request

class REACTLauncher:
    def __init__(self):
        self.tile_server_process = None
        self.main_app_process = None
        self.running = True
        
        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger("REACT.Launcher")
        
    def setup_logging(self):
        """Setup logging for the launcher"""
        # Try to load config to get log file path
        try:
            script_dir = Path(__file__).parent
            config_path = script_dir / "config.yaml"
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            log_file_path = config.get("device_options", {}).get("log_file_path", "data/logs/mission_log.txt")
        except:
            log_file_path = "data/logs/mission_log.txt"
            
        # If path is relative, make it relative to the script directory
        if not os.path.isabs(log_file_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            log_file_path = os.path.join(script_dir, log_file_path)
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file_path, mode='a'),
                logging.StreamHandler()  # Also log to console
            ]
        )
        
    def start_tile_server(self):
        """Start the tile server in background"""
        try:
            self.logger.info("Starting tile server...")
            # Get the directory where launcher.py is located
            script_dir = Path(__file__).parent
            tile_server_path = script_dir / "maps" / "tile_server.py"
            
            # Use the same Python interpreter that's running this script
            self.tile_server_process = subprocess.Popen([
                sys.executable, str(tile_server_path)
            ], 
            cwd=str(script_dir)  # Set working directory to project root
            )
            self.logger.info(f"Tile server started (PID: {self.tile_server_process.pid})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start tile server: {e}")
            return False
    
    def wait_for_tile_server(self, timeout=30):
        """Wait for tile server to be ready"""
        self.logger.info("Waiting for tile server to be ready...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with urllib.request.urlopen("http://127.0.0.1:8081/api/info", timeout=2) as response:
                    if response.status == 200:
                        self.logger.info("Tile server is ready!")
                        return True
            except:
                pass
            time.sleep(1)
        self.logger.warning("Timeout waiting for tile server")
        return False
    
    def start_main_app(self):
        """Start the main REACT application"""
        try:
            self.logger.info("Starting REACT application...")
            # Wait for tile server to be ready
            if not self.wait_for_tile_server():
                self.logger.error("Tile server failed to start properly")
                return False
            
            # Get the directory where launcher.py is located
            script_dir = Path(__file__).parent
            main_app_path = script_dir / "main.py"
            
            self.main_app_process = subprocess.Popen([
                sys.executable, str(main_app_path)
            ], 
            cwd=str(script_dir)  # Set working directory to project root
            )
            self.logger.info(f"REACT application started (PID: {self.main_app_process.pid})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start main application: {e}")
            return False
    
    def stop_processes(self):
        """Stop all processes"""
        self.logger.info("Shutting down REACT...")
        self.running = False
        
        if self.main_app_process:
            self.logger.info("Stopping main application...")
            self.main_app_process.terminate()
            try:
                self.main_app_process.wait(timeout=5)
                self.logger.info("Main application stopped")
            except subprocess.TimeoutExpired:
                self.logger.warning("Force killing main application...")
                self.main_app_process.kill()
        
        if self.tile_server_process:
            self.logger.info("Stopping tile server...")
            self.tile_server_process.terminate()
            try:
                self.tile_server_process.wait(timeout=5)
                self.logger.info("Tile server stopped")
            except subprocess.TimeoutExpired:
                self.logger.warning("Force killing tile server...")
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
                self.logger.info("Main application exited")
                self.running = False
                break
    
    def preload_default_area(self):
        """Preload map tiles around the default position from config"""
        try:
            self.logger.info("Preloading map tiles for default area...")
            config_path = Path(__file__).parent / "config.yaml"
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            default_pos = config.get('default_home_position', {})
            if not default_pos:
                self.logger.info("No default position found in config.yaml, skipping tile preload")
                return True

            lat = default_pos.get('latitude')
            lon = default_pos.get('longitude')
            zoom = default_pos.get('zoom', 12)
            
            if lat is None or lon is None:
                self.logger.warning("Invalid default position in config.yaml, skipping tile preload")
                return True
                
            # Calculate a bounding box around the default position (roughly 10km radius)
            lat_offset = 0.02  # About 11km at equator
            lon_offset = 0.02 / math.cos(math.radians(lat))  # Adjust for latitude
            
            # Preload tiles for zoom levels around default
            min_zoom = max(1, zoom -1)  # 1 levels out
            max_zoom = min(18, zoom + 1)  # 1 levels in

            self.logger.info(f"Default position: {lat:.6f}, {lon:.6f}, zoom {zoom}")
            self.logger.info(f"Preloading area: {lat-lat_offset:.6f},{lon-lon_offset:.6f} to {lat+lat_offset:.6f},{lon+lon_offset:.6f}")
            self.logger.info(f"Zoom levels: {min_zoom} to {max_zoom}")
            
            script_dir = Path(__file__).parent
            tile_server_path = script_dir / "maps" / "tile_server.py"
            
            # Run preload command
            subprocess.run([
                sys.executable, str(tile_server_path), "preload", "satellite",
                str(lat-lat_offset), str(lat+lat_offset), 
                str(lon-lon_offset), str(lon+lon_offset),
                *[str(z) for z in range(min_zoom, max_zoom + 1)]
            ], check=True, cwd=str(script_dir))
            
            self.logger.info("✓ Successfully preloaded map tiles for default area")
            return True
            
        except Exception as e:
            self.logger.warning(f"Failed to preload default area tiles: {e}")
            return True  # Continue anyway

    def run(self):
        """Main launcher function"""
        self.logger.info("=" * 50)
        self.logger.info("REACT Ground Control Station Launcher")
        self.logger.info("=" * 50)
        
        # Set up signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Install dependencies first
        self.logger.info("Installing dependencies...")
        if not install_dependencies():
            self.logger.error("Failed to install dependencies, exiting...")
            return 1
        
        # Start tile server (will automatically preload tiles based on config)
        if not self.start_tile_server():
            self.logger.error("Failed to start tile server, exiting...")
            return 1
        
        # Wait for tile server to be ready
        if not self.wait_for_tile_server():
            self.logger.error("Tile server failed to become ready, exiting...")
            self.stop_processes()
            return 1
        
        # Start main application
        if not self.start_main_app():
            self.logger.error("Failed to start main application, stopping tile server...")
            self.stop_processes()
            return 1
        
        self.logger.info("=" * 50)
        self.logger.info("REACT is running!")
        self.logger.info("- Tile server: http://127.0.0.1:8081")
        self.logger.info("- Main application: Running")
        self.logger.info("Press Ctrl+C to stop all services")
        self.logger.info("=" * 50)
        
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
    logger = logging.getLogger("REACT.Launcher.Dependencies")
    logger.info("Installing tile server dependencies...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "fastapi", "uvicorn", "aiohttp", "aiofiles", "pyyaml"
        ])
        logger.info("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        logger.error("Failed to install dependencies")
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
import sys
import os
import yaml
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from core.app import App

def setup_global_logging(config):
    """Configure logging for the entire application."""
    log_file_path = config.get("device_options", {}).get("log_file_path", "data/logs/mission_log.txt")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    
    # Configure logging globally
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, mode='a'),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    # Log the startup
    logger = logging.getLogger("REACT.Main")
    logger.info("REACT Application logging initialized")
    logger.info(f"Log file: {log_file_path}")

# Function to load configuration
def load_config(path=None):
    if path is None:
        # Get the directory of the currently running script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Construct the path to config.yaml relative to the script's directory
        path = os.path.join(base_dir, "config.yaml")

    try:
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
            print(f"Configuration loaded successfully from: {path}")
            return config
    except FileNotFoundError:
        print(f"Configuration file not found: {path}")
        return {}
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        return {}

def main():
    app = QApplication(sys.argv)

    # Load configuration
    config = load_config()
    
    # Setup global logging first
    setup_global_logging(config)
    
    # Get logger for main
    logger = logging.getLogger("REACT.Main")

    # Initialize backend core
    logger.info("Initializing REACT application...")
    core_app = App(config)
    
    # Start the application
    core_app.start()
    
    # Set up a timer to keep the application running and processing events
    timer = QTimer()
    timer.timeout.connect(lambda: None)  # Keep the event loop active
    timer.start(100)  # Process events every 100ms
    
    try:
        # Run the Qt event loop
        logger.info("Starting Qt event loop...")
        sys.exit(app.exec())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        core_app.stop()

if __name__ == "__main__":
    main()
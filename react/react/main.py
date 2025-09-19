import sys
import os
import yaml
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import QUrl
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
    # Initialize Qt Application
    app = QApplication(sys.argv)

    # Load configuration
    config = load_config()
    
    # Setup global logging first
    setup_global_logging(config)
    
    # Get logger for main
    logger = logging.getLogger("REACT.Main")
    logger.info("Starting REACT Ground Control Station...")

    # Initialize Backend
    logger.info("Initializing backend...")
    backend = App(config)
    backend.start()
    
    # Initialize QML Frontend
    logger.info("Initializing QML frontend...")
    view = QQuickView()
    
    # Expose backend to QML
    view.rootContext().setContextProperty("backend", backend)
    
    # Load main QML file
    qml_dir = os.path.join(os.path.dirname(__file__), "qml")
    qml_file = os.path.join(qml_dir, "MainWindow.qml")
    
    if not os.path.exists(qml_file):
        logger.error(f"QML file not found: {qml_file}")
        backend.stop()
        return
    
    view.setSource(QUrl.fromLocalFile(qml_file))
    view.show()
    
    logger.info("Frontend started successfully")
    
    try:
        # Run the Qt event loop
        logger.info("Starting application event loop...")
        exit_code = app.exec()
        
        # Cleanup
        logger.info("Shutting down...")
        backend.stop()
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        backend.stop()
        app.quit()

if __name__ == "__main__":
    main()
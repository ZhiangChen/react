import sys
import os
import yaml
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineQuick import QtWebEngineQuick
from PySide6.QtWebEngineCore import QWebEngineProfile
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
    # Set Qt style before creating QApplication
    import os
    os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Fusion'
    
    # Initialize Qt Application
    app = QApplication(sys.argv)
    
    # Set style to Fusion to allow Slider customization
    app.setStyle("Fusion")
    
    # Initialize WebEngine with permissive settings
    QtWebEngineQuick.initialize()
    
    # Configure WebEngine profile for local network access
    profile = QWebEngineProfile.defaultProfile()
    
    # Enable local content access
    profile.setHttpUserAgent("REACT Ground Control Station")
    
    # Allow all content
    settings = profile.settings()
    try:
        # These might not all be available in all versions
        if hasattr(settings, 'setAttribute'):
            # Enable various features that might help
            pass
    except Exception as e:
        print(f"Some WebEngine settings not available: {e}")

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
    engine = QQmlApplicationEngine()
    
    # Expose backend to QML
    engine.rootContext().setContextProperty("backend", backend)
    
    # Load main QML file
    qml_dir = os.path.join(os.path.dirname(__file__), "qml")
    qml_file = os.path.join(qml_dir, "MainWindow.qml")
    
    if not os.path.exists(qml_file):
        logger.error(f"QML file not found: {qml_file}")
        backend.stop()
        return
    
    engine.load(QUrl.fromLocalFile(qml_file))
    
    # Check if the QML loaded successfully
    if not engine.rootObjects():
        logger.error("Failed to load QML file")
        backend.stop()
        return
    
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
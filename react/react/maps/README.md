# Maps Service

This directory contains the satellite map visualization service for the REACT Ground Control Station.

## Files

- `tile_server.py` - HTTP server that serves both satellite tiles and the map interface
- `satellite_map.html` - Web-based satellite map interface using Leaflet.js

## Purpose

Provides **real satellite imagery** for the ground control station by:
- Caching satellite tiles from ESRI World Imagery
- Serving both HTML content and tiles from the same HTTP origin (127.0.0.1:8081)
- Bypassing QtWebEngine cross-origin security restrictions
- Delivering interactive map interface to the Qt application

## Architecture

```
Qt Application (main.py)
    ↓
QML MapContainer
    ↓
QtWebEngine → http://127.0.0.1:8081/
    ↓
tile_server.py serves:
    - satellite_map.html (map interface)
    - /tiles/satellite/{z}/{x}/{y}.png (satellite imagery)
```

## Usage

1. Start the tile server: `py -3.12 maps/tile_server.py`
2. Access map interface: http://127.0.0.1:8081/
3. Qt application loads map via QtWebEngine

## Critical QtWebEngine Configuration

**IMPORTANT**: For dynamic tile loading to work in QtWebEngine, the following settings must be enabled in `MapContainer.qml`:

```qml
settings.allowRunningInsecureContent: true
settings.localContentCanAccessRemoteUrls: true  
settings.javascriptEnabled: true
```

### Common Issue: Dynamic Tile Loading Failure

**Symptoms**: 
- Map loads initially but tiles don't load when panning
- Satellite/street map switching works in browser but not in Qt application
- Console shows no tile loading errors but tiles remain blank

**Root Cause**: 
QtWebEngine has strict security policies that block dynamic HTTP requests by default, even from same origin.

**Solution**: 
Ensure the above QtWebEngine settings are present. Without these settings, JavaScript-initiated HTTP requests for tiles will be silently blocked.

**Troubleshooting**:
1. Test in browser first: http://127.0.0.1:8081/ - should work perfectly
2. If browser works but Qt application doesn't → QtWebEngine security settings issue
3. Check QML console for "Same-origin map loaded successfully" message
4. Verify tile server CORS headers are properly configured
5. Ensure WebEngineView URL points to `satellite_map.html` directly: `url: "http://127.0.0.1:8081/satellite_map.html"` (not just the root URL)

## Note

This is **map display/visualization** service, not to be confused with UAV aerial mapping/surveying capabilities.
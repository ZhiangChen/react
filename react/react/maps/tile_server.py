#!/usr/bin/env python3
"""
Local Satellite Tile Server for REACT Ground Control Station
Caches and serves satellite imagery tiles locally
"""

import os
import sys
import asyncio
import aiohttp
import aiofiles
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import math
import hashlib
from pathlib import Path
import logging
from typing import Optional
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    logger.info(f"Loading config from: {config_path.absolute()}")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            logger.info(f"Config loaded successfully. Keys: {list(config.keys())}")
            
            # Get default position
            default_home = config.get("default_home_position", {})
            if not default_home:
                logger.warning("No default_home_position found in config")
                default_home = {
                    "latitude": 37.7749,    # Default to San Francisco
                    "longitude": -122.4194,
                    "zoom": 12
                }
            
            logger.info(f"Default home position: {default_home}")
            return config
    except Exception as e:
        logger.warning(f"Could not load config from {config_path}: {e}")
        return {}

# Load configuration
config = load_config()
map_config = config.get("map_server", {})

# Startup and shutdown events
import contextlib

@contextlib.asynccontextmanager
async def lifespan(app):
    # Startup
    logger.info("REACT Tile Server starting up...")
    logger.info(f"Tile cache directory: {TILE_CACHE_DIR}")
    logger.info(f"Web content directory: {WEB_DIR}")
    yield
    # Shutdown
    await tile_cache.close()
    logger.info("REACT Tile Server shut down")

app = FastAPI(title="REACT Tile Server", version="1.0.0", lifespan=lifespan)

# Enable CORS for QML access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from YAML file
TILE_CACHE_DIR = Path(__file__).parent.parent / "data/tiles"
TILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Web content directory - same directory as this script
WEB_DIR = Path(__file__).parent

# Server configuration
SERVER_HOST = map_config.get("host", "127.0.0.1")
SERVER_PORT = map_config.get("port", 8081)

# Default tile sources (no longer from config)
TILE_SOURCES = {
    "satellite": {
        "name": "Google Satellite",
        "url": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        "attribution": "© Google",
        "max_zoom": 22,
        "headers": {
            "User-Agent": "REACT-GCS/1.0"
        }
    },
    "openstreetmap": {
        "name": "OpenStreetMap",
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "© OpenStreetMap contributors",
        "max_zoom": 22,  # Increased from 18, but tiles may not be available
        "headers": {
            "User-Agent": "REACT-GCS/1.0"
        }
    },
    "esri_satellite": {
        "name": "ESRI Satellite Imagery",
        "url": "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Source: Esri, Maxar, Earthstar Geographics",
        "max_zoom": 22,  # Increased from 19
        "headers": {
            "User-Agent": "REACT-GCS/1.0"
        }
    }
}

class TileCache:
    def __init__(self):
        self.session = None
        
    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
        
    async def close(self):
        if self.session:
            await self.session.close()
    
    def get_tile_path(self, source: str, z: int, x: int, y: int) -> Path:
        """Generate local file path for tile"""
        return TILE_CACHE_DIR / source / str(z) / str(x) / f"{y}.png"
    
    def get_tile_url(self, source: str, z: int, x: int, y: int) -> str:
        """Generate URL for downloading tile"""
        if source not in TILE_SOURCES:
            raise ValueError(f"Unknown tile source: {source}")
        
        source_config = TILE_SOURCES[source]
        return source_config["url"].format(x=x, y=y, z=z)
    
    async def get_tile(self, source: str, z: int, x: int, y: int) -> Optional[bytes]:
        """Get tile from cache only - no downloads in this method"""
        tile_path = self.get_tile_path(source, z, x, y)
        
        # Only check cache
        if tile_path.exists() and tile_path.stat().st_size > 0:
            try:
                logger.info(f"Found tile in cache: {source}/{z}/{x}/{y}")
                async with aiofiles.open(tile_path, 'rb') as f:
                    tile_data = await f.read()
                    if len(tile_data) > 0:
                        return tile_data
                    logger.warning(f"Cached tile is empty: {source}/{z}/{x}/{y}")
            except Exception as e:
                logger.error(f"Error reading cached tile: {e}")
            
        # Return None if not in cache
        logger.info(f"Tile not in cache: {source}/{z}/{x}/{y}")
        return None

# Global tile cache instance
tile_cache = TileCache()

# Mount static files for web content
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")

# Create a simple blank tile for fallback (256x256 transparent PNG)
BLANK_TILE = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
    0x00, 0x00, 0x00, 0x0D,  # IHDR chunk length
    0x49, 0x48, 0x44, 0x52,  # IHDR
    0x00, 0x00, 0x01, 0x00,  # width: 256
    0x00, 0x00, 0x01, 0x00,  # height: 256
    0x08, 0x06, 0x00, 0x00, 0x00,  # bit depth: 8, color type: RGBA, compression: 0, filter: 0, interlace: 0
    0x5C, 0x72, 0xAE, 0x57,  # CRC for IHDR
    0x00, 0x00, 0x00, 0x0C,  # IDAT chunk length
    0x49, 0x44, 0x41, 0x54,  # IDAT
    0x78, 0x9C, 0x62, 0x00, 0x01, 0x00, 0x00, 0x05, 0x00, 0x01, 0x0D, 0x0A,  # compressed transparent pixel data
    0x2D, 0xB4, 0x03, 0x4F,  # CRC for IDAT
    0x00, 0x00, 0x00, 0x00,  # IEND chunk length
    0x49, 0x45, 0x4E, 0x44,  # IEND
    0xAE, 0x42, 0x60, 0x82   # CRC for IEND
])

@app.get("/favicon.ico")
async def favicon():
    """Serve empty favicon to prevent 404 errors"""
    return Response(content=b"", media_type="image/x-icon")

@app.get("/blank_tile.png")
async def get_blank_tile():
    """Serve a blank tile for missing tiles"""
    return Response(
        content=BLANK_TILE,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        }
    )

@app.get("/favicon.ico")
async def favicon():
    """Serve empty favicon to prevent 404 errors"""
    return Response(content=b"", media_type="image/x-icon")

@app.get("/")
async def root():
    """Serve the main map HTML page"""
    logger.info("HTML page requested")
    html_file = WEB_DIR / "satellite_map.html"
    if html_file.exists():
        # Add no-cache headers to prevent caching
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
        return FileResponse(html_file, headers=headers)
    else:
        return {
            "name": "REACT Tile Server",
            "version": "1.0.0",
            "sources": list(TILE_SOURCES.keys()),
            "note": "Place satellite_map.html in maps/ directory to serve the map interface"
        }

@app.get("/api/info")
async def api_info():
    """API information endpoint"""
    logger.info("API info endpoint called")
    # Get default home position from config
    default_home = config.get("default_home_position", {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "zoom": 10
    })
    logger.info(f"Returning default_home_position: {default_home}")
    
    response = {
        "name": "REACT Tile Server API",
        "version": "1.0.0",
        "sources": list(TILE_SOURCES.keys()),
        "default_home_position": default_home
    }
    logger.info(f"Full API response: {response}")
    return response

@app.get("/sources")
async def get_sources():
    """Get available tile sources - legacy endpoint"""
    return TILE_SOURCES

@app.get("/api/sources")
async def get_api_sources():
    """Get available tile sources"""
    return TILE_SOURCES

@app.get("/api/config")
async def get_config():
    """Serve config.yaml as JSON"""
    try:
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading config: {str(e)}")

@app.get("/tiles/{source}/{z}/{x}/{y}.png")
async def get_tile_endpoint(source: str, z: int, x: int, y: int):
    """Serve tile image with strict cache-first approach"""
    logger.info(f"Tile requested: {source}/{z}/{x}/{y}")
    
    if source not in TILE_SOURCES:
        logger.error(f"Unknown tile source: {source}")
        raise HTTPException(status_code=404, detail=f"Source '{source}' not found")
    
    # Validate zoom level
    max_zoom = TILE_SOURCES[source]["max_zoom"]
    if z > max_zoom:
        logger.error(f"Zoom level {z} exceeds maximum {max_zoom} for source {source}")
        raise HTTPException(status_code=400, detail=f"Zoom level {z} exceeds maximum {max_zoom}")
    
    # Validate tile coordinates
    max_tile = 2 ** z
    if x >= max_tile or y >= max_tile or x < 0 or y < 0:
        logger.error(f"Invalid tile coordinates: {x},{y} for zoom {z}")
        raise HTTPException(status_code=400, detail="Invalid tile coordinates")
    
    # Get tile path
    tile_path = tile_cache.get_tile_path(source, z, x, y)
    logger.info(f"Looking for cached tile at: {tile_path}")
    
    # First check if tile exists in cache
    if tile_path.exists():
        file_size = tile_path.stat().st_size
        logger.info(f"Found cached tile, size: {file_size} bytes")
        
        if file_size > 0:
            logger.info(f"Serving cached tile: {source}/{z}/{x}/{y}")
            return FileResponse(
                tile_path,
                media_type="image/png",
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                }
            )
        else:
            logger.warning(f"Cached tile is empty: {source}/{z}/{x}/{y}")
    else:
        logger.info(f"Tile not found in cache: {source}/{z}/{x}/{y}")
    
    # Only try to download if we can connect to internet quickly
    try:
        # Very quick connectivity test
        connector = aiohttp.TCPConnector(limit=1, limit_per_host=1)
        timeout = aiohttp.ClientTimeout(total=0.5, connect=0.5)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            url = TILE_SOURCES[source]["url"].format(x=x, y=y, z=z)
            headers = TILE_SOURCES[source]["headers"]
            
            logger.info(f"Attempting quick download: {source}/{z}/{x}/{y}")
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    tile_data = await response.read()
                    if len(tile_data) > 0:
                        # Cache the newly downloaded tile
                        tile_path.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            async with aiofiles.open(tile_path, 'wb') as f:
                                await f.write(tile_data)
                            logger.info(f"Downloaded and cached: {source}/{z}/{x}/{y}")
                        except Exception as e:
                            logger.error(f"Error caching tile: {e}")
                        
                        return Response(
                            content=tile_data,
                            media_type="image/png",
                            headers={
                                "Cache-Control": "public, max-age=86400",
                                "Access-Control-Allow-Origin": "*",
                                "Access-Control-Allow-Methods": "GET, OPTIONS",
                                "Access-Control-Allow-Headers": "*",
                            }
                        )
                else:
                    logger.warning(f"Download failed with status {response.status}")
    except Exception as e:
        logger.info(f"Network unavailable (offline mode): {e}")
    
    # If we get here, tile is not available - return blank tile instead of 404
    logger.info(f"Returning blank tile for: {source}/{z}/{x}/{y}")
    return Response(
        content=BLANK_TILE,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Add OSM-compatible tile endpoint
@app.get("/{z}/{x}/{y}.png")
async def get_osm_tile_endpoint(z: int, x: int, y: int):
    """Serve tile image in OSM format (satellite by default)"""
    return await get_tile_endpoint("satellite", z, x, y)

@app.get("/cache/info")
async def cache_info():
    """Get cache statistics"""
    total_tiles = 0
    cache_size = 0
    
    for source_dir in TILE_CACHE_DIR.iterdir():
        if source_dir.is_dir():
            for tile_file in source_dir.rglob("*.png"):
                total_tiles += 1
                cache_size += tile_file.stat().st_size
    
    return {
        "total_tiles": total_tiles,
        "cache_size_mb": round(cache_size / (1024 * 1024), 2),
        "cache_directory": str(TILE_CACHE_DIR)
    }

@app.delete("/cache/clear")
async def clear_cache():
    """Clear tile cache"""
    import shutil
    try:
        if TILE_CACHE_DIR.exists():
            shutil.rmtree(TILE_CACHE_DIR)
            TILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")

# Utility function to pre-download tiles for a region
async def preload_region(source: str, lat_min: float, lat_max: float, 
                        lon_min: float, lon_max: float, zoom_levels: list):
    """Pre-download tiles for a geographic region"""
    logger.info(f"Pre-loading region: {lat_min},{lon_min} to {lat_max},{lon_max} at zooms {zoom_levels}")
    
    def deg2num(lat_deg, lon_deg, zoom):
        """Convert lat/lon to tile numbers"""
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        x = int((lon_deg + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return (x, y)
    
    total_tiles = 0
    for zoom in zoom_levels:
        x_min, y_max = deg2num(lat_min, lon_min, zoom)
        x_max, y_min = deg2num(lat_max, lon_max, zoom)
        
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                await tile_cache.get_tile(source, zoom, x, y)
                total_tiles += 1
                
                # Add small delay to be nice to servers
                await asyncio.sleep(0.1)
    
    logger.info(f"Pre-loaded {total_tiles} tiles")

@app.get("/satellite_map.html")
async def satellite_map():
    """Serve the satellite map HTML page directly"""
    logger.info("Satellite map HTML requested")
    html_file = WEB_DIR / "satellite_map.html"
    if html_file.exists():
        # Add no-cache headers to prevent caching
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
        return FileResponse(html_file, headers=headers)
    else:
        return {"error": "satellite_map.html not found"}

async def preload_default_area():
    """Preload tiles for the default area from config"""
    try:
        preload = config.get('tile_preload', {})
        if not preload:
            logger.warning("No tile preload configuration found")
            return
            
        lat = preload['latitude']
        lon = preload['longitude']
        radius_km = preload['radius_km']
        min_zoom = preload['min_zoom']
        max_zoom = preload['max_zoom']
        
        # Convert radius to lat/lon offset (approximate)
        # 1 degree latitude = 111km
        lat_offset = radius_km / 111.0
        # Adjust longitude offset based on latitude
        lon_offset = lat_offset / math.cos(math.radians(lat))
        
        lat_min = lat - lat_offset
        lat_max = lat + lat_offset
        lon_min = lon - lon_offset
        lon_max = lon + lon_offset
        zoom_levels = list(range(min_zoom, max_zoom + 1))
        
        logger.info(f"Preloading tiles for default area:")
        logger.info(f"Center: {lat}, {lon}")
        logger.info(f"Coverage: {lat_min},{lon_min} to {lat_max},{lon_max}")
        logger.info(f"Zoom levels: {zoom_levels}")
        
        await preload_region("satellite", lat_min, lat_max, lon_min, lon_max, zoom_levels)
        logger.info("✓ Default area tiles preloaded successfully")
        
    except Exception as e:
        logger.error(f"Error preloading default area: {e}")

if __name__ == "__main__":
    # Run the server using configured host and port
    logger.info(f"Starting REACT Tile Server on http://{SERVER_HOST}:{SERVER_PORT}")
    logger.info("Serving HTML content and satellite tiles from same origin")
    
    # Preload default area tiles on startup
    asyncio.run(preload_default_area())
    
    # Start the server
    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=False,
        log_level="info"
    )
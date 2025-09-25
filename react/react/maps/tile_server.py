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
            default_home = config.get("default_home_position")
            logger.info(f"Default home position in config: {default_home}")
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
        "max_zoom": 20,
        "headers": {
            "User-Agent": "REACT-GCS/1.0"
        }
    },
    "openstreetmap": {
        "name": "OpenStreetMap",
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "© OpenStreetMap contributors",
        "max_zoom": 18,
        "headers": {
            "User-Agent": "REACT-GCS/1.0"
        }
    },
    "esri_satellite": {
        "name": "ESRI Satellite Imagery",
        "url": "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Source: Esri, Maxar, Earthstar Geographics",
        "max_zoom": 19,
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
        """Get tile from cache or download if not available - Simplified stable version"""
        tile_path = self.get_tile_path(source, z, x, y)
        
        # Check if tile exists in cache and has content
        if tile_path.exists() and tile_path.stat().st_size > 0:
            try:
                logger.info(f"Serving cached tile: {source}/{z}/{x}/{y}")
                async with aiofiles.open(tile_path, 'rb') as f:
                    tile_data = await f.read()
                    if len(tile_data) > 0:
                        return tile_data
                    else:
                        logger.warning(f"Cached tile is empty, will re-download: {source}/{z}/{x}/{y}")
                        # Remove empty file
                        tile_path.unlink()
            except Exception as e:
                logger.error(f"Error reading cached tile: {e}")
                # Remove corrupted file
                try:
                    tile_path.unlink()
                except:
                    pass
        
        # Download tile if not in cache
        try:
            session = await self.get_session()
            url = self.get_tile_url(source, z, x, y)
            headers = TILE_SOURCES[source]["headers"]
            
            logger.info(f"Downloading tile: {source}/{z}/{x}/{y}")
            
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    tile_data = await response.read()
                    
                    # Cache the tile
                    tile_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        async with aiofiles.open(tile_path, 'wb') as f:
                            await f.write(tile_data)
                        logger.info(f"✓ Downloaded and cached tile: {source}/{z}/{x}/{y} ({len(tile_data)} bytes)")
                    except Exception as e:
                        logger.error(f"Error caching tile: {e}")
                    
                    return tile_data
                else:
                    logger.warning(f"Failed to download tile {source}/{z}/{x}/{y}: {response.status}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout downloading tile: {source}/{z}/{x}/{y}")
            return None
        except Exception as e:
            logger.error(f"Error downloading tile {source}/{z}/{x}/{y}: {e}")
            return None

# Global tile cache instance
tile_cache = TileCache()

# Mount static files for web content
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

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
    """Serve tile image"""
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
    
    try:
        logger.info(f"Getting tile from cache: {source}/{z}/{x}/{y}")
        tile_data = await tile_cache.get_tile(source, z, x, y)
        if tile_data:
            logger.info(f"Serving tile: {source}/{z}/{x}/{y} ({len(tile_data)} bytes)")
            return Response(
                content=tile_data,
                media_type="image/png",
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                    "Access-Control-Allow-Origin": "http://127.0.0.1:8081",  # Specific origin for QtWebEngine
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",  # Allow credentials for same-origin
                    "X-Content-Type-Options": "nosniff",  # Security header
                    "Content-Security-Policy": "default-src 'self'"  # CSP for QtWebEngine
                }
            )
        else:
            logger.error(f"Tile not available: {source}/{z}/{x}/{y}")
            raise HTTPException(status_code=404, detail="Tile not available")
            
    except Exception as e:
        logger.error(f"Error serving tile {source}/{z}/{x}/{y}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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

if __name__ == "__main__":
    # Command line interface for running server or pre-loading tiles
    if len(sys.argv) > 1 and sys.argv[1] == "preload":
        # Example: python tile_server.py preload satellite 40.0 41.0 -74.0 -73.0 10 11 12
        if len(sys.argv) < 8:
            print("Usage: python tile_server.py preload <source> <lat_min> <lat_max> <lon_min> <lon_max> <zoom1> [zoom2] ...")
            sys.exit(1)
        
        source = sys.argv[2]
        lat_min = float(sys.argv[3])
        lat_max = float(sys.argv[4])
        lon_min = float(sys.argv[5])
        lon_max = float(sys.argv[6])
        zoom_levels = [int(z) for z in sys.argv[7:]]
        
        asyncio.run(preload_region(source, lat_min, lat_max, lon_min, lon_max, zoom_levels))
    else:
        # Run the server using configured host and port
        logger.info(f"Starting REACT Tile Server on http://{SERVER_HOST}:{SERVER_PORT}")
        logger.info("Serving HTML content and satellite tiles from same origin")
        uvicorn.run(
            app,
            host=SERVER_HOST,
            port=SERVER_PORT,
            reload=False,
            log_level="info"
        )
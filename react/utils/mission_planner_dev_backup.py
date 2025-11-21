#!/usr/bin/env python3
"""
Mission Planner Development Tool - Survey Grid Generator

README:
-------
This script replicates Mission Planner's "Survey (Grid)" tool for photogrammetry missions.

Requirements:
    pip install matplotlib numpy

Usage:
    python mission_planner_dev.py          # Interactive mode
    python mission_planner_dev.py --test   # Test mode with predefined polygon

Instructions:
    1. Left-click to add polygon vertices
    2. Press 'Enter' or right-click to close the polygon
    3. Enter reference coordinates when prompted
    4. Flight path will be generated and displayed
    5. Waypoints will be saved to a .waypoints file

Configuration:
    Edit the MISSION_PARAMS dictionary below to change flight parameters

MODULE STRUCTURE:
    Section 1:  Coordinate Conversion Utilities
    Section 2:  Camera & Mission Calculation Utilities
    Section 3:  Geometry & Intersection Utilities
    Section 4:  Polygon Decomposition Algorithms
    Section 5:  Survey Grid Generation Core (Main Algorithm)
    Section 6:  Mission Statistics & Analysis
    Section 7:  Visualization & Display Helpers
    Section 8:  Interactive UI Event Handlers
    Section 9:  Main Application Entry Point
"""

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
import numpy as np
import math
import sys

# ============================================================================
# MISSION PARAMETERS - EDIT THESE VALUES
# ============================================================================
MISSION_PARAMS = {
    'altitude': 50,              # Flight altitude in meters AGL
    'forward_overlap': 70,       # Forward (front) overlap in %
    'lateral_overlap': 70,       # Lateral (side) overlap in %
    'camera_hfov': 73.4,         # Horizontal field of view in degrees
    'camera_vfov': 52.0,         # Vertical field of view in degrees
    'camera_width': 6000,        # Image width in pixels
    'camera_height': 4000,       # Image height in pixels
    'aircraft_speed': 10,        # Speed in m/s
    'grid_angle': None,          # Grid angle in degrees (None = auto-detect longest edge)
}

# Global state
polygon_points = []
polygon_closed = False
waypoints = []

# Fixed reference point at map origin (can be edited here)
reference_lat = 34.163808   # Default latitude (from config.yaml)
reference_lon = -118.074877  # Default longitude (from config.yaml)

fig = None
ax = None
fig_cells = None  # Global for cell visualization canvas
ax_cells = None   # Global for cell visualization axes
polygon_patch = None
line = None


# ============================================================================
# SECTION 1: COORDINATE CONVERSION FUNCTIONS
# Converts between lat/lon and meters using flat-earth approximation
# ============================================================================
# SECTION 1B: GEOMETRY HELPER FUNCTIONS
# Common geometric calculations used throughout the code
# ============================================================================

def euclidean_distance(p1, p2):
    """
    Calculate Euclidean distance between two points.
    
    Args:
        p1: Tuple (x, y) for first point
        p2: Tuple (x, y) for second point
    
    Returns:
        Distance as float
    """
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)


def polyline_length(vertices, polygon_vertices):
    """
    Calculate total length of a polyline.
    
    Args:
        vertices: List of vertex indices
        polygon_vertices: List of (x, y) coordinate tuples
    
    Returns:
        Total length as float
    """
    length = 0.0
    for i in range(len(vertices) - 1):
        p1 = polygon_vertices[vertices[i]]
        p2 = polygon_vertices[vertices[i + 1]]
        length += euclidean_distance(p1, p2)
    return length


def convert_to_canvas_coords(points_m, scale, origin_x, origin_y):
    """
    Batch convert meter coordinates to canvas coordinates.
    
    Args:
        points_m: List of (x_m, y_m) tuples in meters
        scale: Scaling factor
        origin_x, origin_y: Canvas origin
    
    Returns:
        List of (px, py) tuples in canvas coordinates
    """
    return [(x_m / scale + origin_x, y_m / scale + origin_y) for x_m, y_m in points_m]


# ============================================================================
# SECTION 2: CAMERA & MISSION CALCULATION UTILITIES
# Calculates GSD, line spacing, and photo distances based on flight parameters
# ============================================================================
def calculate_ground_footprint(altitude, hfov, vfov):
    """
    Calculate camera ground footprint at given altitude.
    
    Returns: (width_meters, height_meters)
    """
    hfov_rad = math.radians(hfov)
    vfov_rad = math.radians(vfov)
    
    width = 2 * altitude * math.tan(hfov_rad / 2)
    height = 2 * altitude * math.tan(vfov_rad / 2)
    
    return width, height


def calculate_gsd(altitude, hfov, image_width):
    """
    Calculate Ground Sampling Distance (GSD) in cm/pixel.
    """
    footprint_width = 2 * altitude * math.tan(math.radians(hfov) / 2)
    gsd_m = footprint_width / image_width
    gsd_cm = gsd_m * 100
    return gsd_cm


def calculate_line_spacing(altitude, hfov, lateral_overlap):
    """
    Calculate spacing between parallel survey lines.
    
    spacing = image_footprint_width × (1 - lateral_overlap/100)
    """
    footprint_width, _ = calculate_ground_footprint(altitude, hfov, MISSION_PARAMS['camera_vfov'])
    spacing = footprint_width * (1.0 - lateral_overlap / 100.0)
    return spacing


def calculate_photo_distance(altitude, vfov, forward_overlap):
    """
    Calculate distance between photo captures.
    
    distance = image_footprint_height × (1 - forward_overlap/100)
    """
    _, footprint_height = calculate_ground_footprint(altitude, MISSION_PARAMS['camera_hfov'], vfov)
    distance = footprint_height * (1.0 - forward_overlap / 100.0)
    return distance


# ============================================================================
# SECTION 3: GEOMETRY & INTERSECTION UTILITIES
# Core geometric functions for polygon operations, line intersections
# ============================================================================
def point_in_polygon(point, polygon):
    """
    Check if point is inside polygon using ray casting algorithm.
    
    Args:
        point: (x, y) tuple
        polygon: list of (x, y) tuples
        
    Returns: True if inside, False otherwise
    """
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside


def line_segment_intersection(p1, p2, p3, p4):
    """
    Find intersection point of two line segments.
    
    Args:
        p1, p2: endpoints of first segment
        p3, p4: endpoints of second segment
        
    Returns: (x, y) intersection point or None
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-10:
        return None  # Parallel lines
    
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
    
    if 0 <= t <= 1 and 0 <= u <= 1:
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        return (x, y)
    
    return None



def calculate_turning_angle(edge1_start, edge1_end, edge2_start, edge2_end):
    """
    Calculate the turning angle between two consecutive edges.
    
    Args:
        edge1_start, edge1_end: endpoints of first edge
        edge2_start, edge2_end: endpoints of second edge
        
    Returns: turning angle in degrees (0-180, absolute value)
    """
    # Vector of first edge
    dx1 = edge1_end[0] - edge1_start[0]
    dy1 = edge1_end[1] - edge1_start[1]
    
    # Vector of second edge
    dx2 = edge2_end[0] - edge2_start[0]
    dy2 = edge2_end[1] - edge2_start[1]
    
    # Calculate angles of both edges
    angle1 = math.atan2(dy1, dx1)
    angle2 = math.atan2(dy2, dx2)
    
    # Calculate turning angle
    angle_diff = angle2 - angle1
    
    # Normalize to -180 to 180
    while angle_diff > math.pi:
        angle_diff -= 2 * math.pi
    while angle_diff < -math.pi:
        angle_diff += 2 * math.pi
    
    # Return absolute value in degrees
    return abs(math.degrees(angle_diff))


# ============================================================================
# SECTION 4: POLYGON DECOMPOSITION ALGORITHMS
# Decomposes complex polygons into simpler polylines for survey planning
# ============================================================================
def decompose_into_polylines(polygon, angle_threshold):
    """
    Decompose polygon into polylines based on angular continuity.
    
    Edges are grouped into the same polyline if the turning angle between
    consecutive edges is less than the threshold (nearly straight).
    
    This implementation is start-point independent: it finds all corner vertices
    (sharp turns) first, then creates polylines between consecutive corners.
    
    Args:
        polygon: list of (x, y) vertices
        angle_threshold: maximum turning angle (degrees) for same polyline
        
    Returns: list of polylines, each polyline is a list of consecutive vertex indices
    """
    if len(polygon) < 3:
        return [[i for i in range(len(polygon))]]
    
    n = len(polygon)
    
    # STEP 1: Identify all corner vertices (sharp turns)
    # A vertex is a corner if the turning angle at that vertex exceeds the threshold
    corner_indices = []
    
    for i in range(n):
        # Get consecutive edges around vertex i
        prev_vertex = polygon[(i - 1) % n]
        curr_vertex = polygon[i]
        next_vertex = polygon[(i + 1) % n]
        
        # Calculate turning angle at this vertex
        angle = calculate_turning_angle(prev_vertex, curr_vertex, curr_vertex, next_vertex)
        
        # If angle is large (sharp turn), mark as corner
        if angle >= angle_threshold:
            corner_indices.append(i)
    
    # If no corners found, entire polygon is one polyline
    if len(corner_indices) == 0:
        return [[i for i in range(n)]]
    
    # STEP 2: Create polylines between consecutive corners
    polylines = []
    num_corners = len(corner_indices)
    
    for i in range(num_corners):
        start_corner = corner_indices[i]
        end_corner = corner_indices[(i + 1) % num_corners]
        
        # Build polyline from start_corner to end_corner (inclusive)
        polyline = []
        
        if end_corner > start_corner:
            # Normal case: no wrap-around
            polyline = list(range(start_corner, end_corner + 1))
        else:
            # Wrap-around case: goes past the last vertex
            polyline = list(range(start_corner, n)) + list(range(0, end_corner + 1))
        
        if len(polyline) >= 2:
            polylines.append(polyline)
    
    return polylines


def adaptive_polyline_decomposition(polygon, target_polylines=4):
    """
    Automatically find the angle threshold that decomposes polygon into
    approximately target_polylines segments using adaptive step size.
    
    Uses a sophisticated search algorithm that:
    1. Starts with a coarse step size (5°)
    2. When overshooting (e.g., 3→5 polylines), reduces step size by half
    3. Searches backward to find the exact threshold
    4. Iteratively refines until finding the target or getting close enough
    
    Args:
        polygon: list of (x, y) vertices
        target_polylines: desired number of polylines (default 4)
        
    Returns: (polylines, threshold_used)
    """
    n = len(polygon)
    
    # For triangles, target should be 3
    if n == 3:
        target_polylines = 3
    
    print(f"\nAdaptive polyline decomposition (target: {target_polylines} polylines)")
    print("-" * 60)
    
    # Start with initial parameters
    current_threshold = 180
    step_size = 5.0  # Start with 5° steps
    min_step = 0.5   # Minimum step size for refinement
    
    prev_threshold = None
    prev_num_polylines = None
    best_polylines = None
    best_threshold = None
    best_diff = float('inf')  # Track closest match
    
    iteration = 0
    max_iterations = 200  # Safety limit
    
    while current_threshold > 0 and iteration < max_iterations:
        iteration += 1
        
        # Ensure threshold is positive
        if current_threshold < 0:
            current_threshold = 0.5
        
        polylines = decompose_into_polylines(polygon, current_threshold)
        num_polylines = len(polylines)
        
        print(f"Threshold {current_threshold:6.2f}° (step={step_size:5.2f}°): {num_polylines} polylines")
        
        # Track the closest result to target
        diff = abs(num_polylines - target_polylines)
        if diff < best_diff or (diff == best_diff and num_polylines >= target_polylines):
            best_diff = diff
            best_polylines = polylines
            best_threshold = current_threshold
        
        # Check if we hit the target exactly
        if num_polylines == target_polylines:
            print(f"✓ Found exact match!")
            break
        
        # Check if we overshot the target
        if prev_num_polylines is not None:
            # Detect overshoot: jumped over the target
            if prev_num_polylines < target_polylines and num_polylines > target_polylines:
                print(f"  → Overshot! ({prev_num_polylines} → {num_polylines}, target={target_polylines})")
                
                # If step size is still large, reduce it and search backward
                if step_size > min_step:
                    step_size = step_size / 2.0
                    current_threshold = prev_threshold  # Go back to previous position
                    print(f"  → Reducing step size to {step_size:.2f}° and searching backward")
                    prev_num_polylines = None  # Reset to avoid double detection
                    continue
                else:
                    # Step size is already minimal, accept best result
                    print(f"  → Step size minimal ({step_size:.2f}°), accepting closest result")
                    break
            
            # Also detect when we reach or exceed target from below
            if prev_num_polylines < target_polylines and num_polylines >= target_polylines:
                # We just crossed the threshold, refine if possible
                if step_size > min_step and num_polylines > target_polylines:
                    step_size = step_size / 2.0
                    current_threshold = prev_threshold
                    print(f"  → Crossed target, refining with step size {step_size:.2f}°")
                    prev_num_polylines = None
                    continue
                else:
                    # Good enough
                    break
        
        # Store previous state
        prev_threshold = current_threshold
        prev_num_polylines = num_polylines
        
        # Move to next threshold
        current_threshold -= step_size
    
    # Safety fallback
    if best_polylines is None:
        print(f"Warning: No decomposition found, using threshold=5°")
        best_threshold = 5
        best_polylines = decompose_into_polylines(polygon, best_threshold)
    
    print(f"\n✓ Selected threshold: {best_threshold:.2f}° → {len(best_polylines)} polylines")
    print(f"  Target: {target_polylines}, Achieved: {len(best_polylines)}, Diff: {abs(len(best_polylines) - target_polylines)}")
    print("-" * 60)
    
    return best_polylines, best_threshold

def get_longest_edge_angle(polygon):
    """
    Find the angle of the longest edge of the polygon.
    This will be used as the grid orientation.
    
    Returns: angle in degrees (0-180)
    """
    max_length = 0
    best_angle = 0
    
    n = len(polygon)
    for i in range(n):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % n]
        
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = euclidean_distance(p1, p2)
        
        if length > max_length:
            max_length = length
            # Calculate angle (0-180 degrees)
            angle = math.degrees(math.atan2(dy, dx))
            # Normalize to 0-180
            if angle < 0:
                angle += 180
            best_angle = angle
    
    return best_angle


# ============================================================================
# HELPER FUNCTIONS FOR CELL DECOMPOSITION AND WAYPOINT GENERATION
# ============================================================================

def build_connectivity_graph(polygon_vertices, polyline_list):
    """
    Build adjacency graph from polylines showing vertex connectivity.
    
    Args:
        polygon_vertices: List of (x, y) coordinates
        polyline_list: List of polylines (each is list of vertex indices)
    
    Returns:
        Dictionary mapping vertex_idx -> [connected_vertex_indices]
    """
    adjacency = {}
    
    # Initialize all vertices
    for i in range(len(polygon_vertices)):
        adjacency[i] = []
    
    # Add edges from polylines
    for polyline_indices in polyline_list:
        for i in range(len(polyline_indices) - 1):
            v1 = polyline_indices[i]
            v2 = polyline_indices[i + 1]
            
            if v2 not in adjacency[v1]:
                adjacency[v1].append(v2)
            if v1 not in adjacency[v2]:
                adjacency[v2].append(v1)
    
    return adjacency


def find_clockwise_boundary(adjacency, start_vertex=None):
    """
    Traverse polygon boundary in clockwise order using connectivity.
    
    Args:
        adjacency: Connectivity graph
        start_vertex: Optional starting vertex (default: vertex 0)
    
    Returns:
        List of vertex indices in clockwise order
    """
    if start_vertex is None:
        # Start from vertex 0 or first available vertex
        start_vertex = 0
        if start_vertex not in adjacency or len(adjacency[start_vertex]) == 0:
            # Find first vertex with connections
            for v in sorted(adjacency.keys()):
                if len(adjacency[v]) > 0:
                    start_vertex = v
                    break
    
    boundary = []
    visited = set()
    current = start_vertex
    
    while True:
        boundary.append(current)
        visited.add(current)
        
        # Find next unvisited neighbor
        neighbors = adjacency.get(current, [])
        next_vertex = None
        
        for neighbor in neighbors:
            if neighbor not in visited:
                next_vertex = neighbor
                break
        
        if next_vertex is None:
            # Check if we can close the loop
            if start_vertex in neighbors and len(boundary) > 2:
                break
            else:
                # Dead end or isolated vertex
                break
        
        current = next_vertex
    
    return boundary


def find_longest_polyline_start(polyline_list, polygon_vertices):
    """
    Find the starting vertex of the longest polyline.
    This provides a deterministic starting point for decomposition.
    
    Args:
        polyline_list: List of polylines
        polygon_vertices: List of (x, y) coordinates
    
    Returns:
        Index of the first vertex of the longest polyline
    """
    max_length = 0
    longest_start = 0
    
    for polyline_indices in polyline_list:
        # Calculate polyline length using helper function
        length = polyline_length(polyline_indices, polygon_vertices)
        
        if length > max_length:
            max_length = length
            longest_start = polyline_indices[0]
    
    return longest_start


def decompose_cell_recursive(polygon_vertices, polyline_list, pairs_list, 
                             adjacency, boundary_order, cell_list, depth=0):
    """
    Recursively decompose polygon into cells using corresponding pairs.
    
    Args:
        polygon_vertices: List of (x, y) coordinates (can grow with insertions)
        polyline_list: List of polylines
        pairs_list: List of corresponding pairs (sorted)
        adjacency: Connectivity graph
        boundary_order: Clockwise boundary traversal
        cell_list: Accumulator for cells
        depth: Recursion depth for debugging
    """
    indent = "  " * depth
    print(f"{indent}[Depth {depth}] Decomposing polygon with {len(boundary_order)} boundary vertices")
    print(f"{indent}  Boundary: {boundary_order}")
    print(f"{indent}  Available pairs: {len(pairs_list)}")
    
    if len(pairs_list) == 0:
        # No more pairs - entire remaining polygon is one cell
        cell_vertices = [polygon_vertices[idx] for idx in boundary_order]
        cell_list.append(cell_vertices)
        print(f"{indent}  ✓ Terminal cell: {len(cell_vertices)} vertices\n")
        return
    
    # Take the first pair (closest to start of boundary)
    pair = pairs_list[0]
    remaining_pairs = pairs_list[1:]
    
    p1_idx = pair['point_1_idx']
    p2_idx = pair['point_2_idx']
    
    print(f"{indent}  Using pair: {p1_idx} ↔ {p2_idx}")
    
    # Find positions of pair vertices in boundary
    try:
        p1_pos = boundary_order.index(p1_idx)
        p2_pos = boundary_order.index(p2_idx)
    except ValueError:
        print(f"{indent}  ⚠ Pair vertices not in boundary, skipping")
        # Skip this pair and try next
        decompose_cell_recursive(polygon_vertices, polyline_list, remaining_pairs,
                                adjacency, boundary_order, cell_list, depth)
        return
    
    print(f"{indent}  Pair positions in boundary: {p1_pos}, {p2_pos}")
    
    # Create first cell: from start to pair
    cell1_boundary = []
    
    # Trace from start (0) to p1_pos
    for i in range(p1_pos + 1):
        cell1_boundary.append(boundary_order[i])
    
    # Add p2_idx (crossing the pair)
    cell1_boundary.append(p2_idx)
    
    # Trace from p2_pos+1 back to start (wrapping)
    for i in range(p2_pos + 1, len(boundary_order)):
        cell1_boundary.append(boundary_order[i])
    
    # Convert to coordinates
    cell1_vertices = [polygon_vertices[idx] for idx in cell1_boundary]
    cell_list.append(cell1_vertices)
    
    print(f"{indent}  ✓ Cell {len(cell_list)-1}: {len(cell1_vertices)} vertices")
    print(f"{indent}    Boundary indices: {cell1_boundary}\n")
    
    # Create remaining polygon boundary: from p1 to p2 (the other side)
    remaining_boundary = []
    
    # Trace from p1_pos to p2_pos along boundary
    pos = p1_pos
    while True:
        remaining_boundary.append(boundary_order[pos])
        if pos == p2_pos:
            break
        pos = (pos + 1) % len(boundary_order)
    
    print(f"{indent}  Remaining polygon: {len(remaining_boundary)} boundary vertices")
    print(f"{indent}    Boundary: {remaining_boundary}")
    
    # Filter pairs: keep only pairs where both vertices are in remaining boundary
    remaining_boundary_set = set(remaining_boundary)
    filtered_pairs = []
    for p in remaining_pairs:
        if p['point_1_idx'] in remaining_boundary_set and p['point_2_idx'] in remaining_boundary_set:
            filtered_pairs.append(p)
    
    print(f"{indent}  Filtered pairs: {len(filtered_pairs)} (from {len(remaining_pairs)})\n")
    
    # Recursively decompose remaining polygon
    if len(remaining_boundary) > 2:
        decompose_cell_recursive(polygon_vertices, polyline_list, filtered_pairs,
                                adjacency, remaining_boundary, cell_list, depth + 1)


def edge_matches(edge_v1, edge_v2, target_v1, target_v2, tolerance=0.1):
    """
    Check if two edges match (in either direction).
    
    Args:
        edge_v1, edge_v2: Vertices of first edge
        target_v1, target_v2: Vertices of second edge
        tolerance: Maximum distance for vertices to be considered matching
        
    Returns:
        bool: True if edges match in forward or reverse direction
    """
    dist1 = euclidean_distance(edge_v1, target_v1)
    dist2 = euclidean_distance(edge_v2, target_v2)
    forward_match = dist1 < tolerance and dist2 < tolerance
    
    dist1_rev = euclidean_distance(edge_v1, target_v2)
    dist2_rev = euclidean_distance(edge_v2, target_v1)
    reverse_match = dist1_rev < tolerance and dist2_rev < tolerance
    
    return forward_match or reverse_match


# ============================================================================
# SURVEY GRID GENERATION (Mission Planner Algorithm)
# ============================================================================

def slice_cell_with_lines(cell, edge_labels, start_offset, line_spacing):
    """
    Slice a cell polygon with parallel lines based on corresponding edges.
    
    Scenarios:
    1. Two corresponding edges: Generate uniform points along both edges with start_offset,
       connect corresponding points to form slicing lines
    2. One corresponding edge: Generate uniform points along it with start_offset,
       shoot rays in direction edge orientation to find intersections
    3. No corresponding edges: Perpendicular slicing from direction edge with line_spacing
    
    Args:
        cell: List of (x, y) vertices defining the cell polygon
        edge_labels: List of (v1, v2, label) tuples for each edge
        start_offset: Starting offset from direction edge along corresponding edge
        line_spacing: Distance between parallel lines along corresponding edge
        
    Returns:
        List of line segments, each as ((x1, y1), (x2, y2)) in original coordinates
    """
    # Extract edges by label
    direction_edge = None
    corresponding_edges = []
    
    for v1, v2, label in edge_labels:
        if label == 2:  # Direction edge
            direction_edge = (v1, v2)
        elif label == 3:  # Corresponding edge
            corresponding_edges.append((v1, v2))
    
    if direction_edge is None:
        print("  ⚠ No direction edge found in cell")
        return []
    
    num_corresponding = len(corresponding_edges)
    print(f"  Found {num_corresponding} corresponding edge(s)")
    
    dir_v1, dir_v2 = direction_edge
    
    # Calculate direction edge vector (normalized)
    dir_dx = dir_v2[0] - dir_v1[0]
    dir_dy = dir_v2[1] - dir_v1[1]
    dir_length = math.sqrt(dir_dx**2 + dir_dy**2)
    
    if dir_length < 1e-10:
        print("  ⚠ Direction edge has zero length")
        return []
    
    dir_nx = dir_dx / dir_length
    dir_ny = dir_dy / dir_length
    
    # ========================================================================
    # SCENARIO 1: TWO CORRESPONDING EDGES
    # Generate uniform points along both edges, connect corresponding points
    # Start point: offset from the END of direction edge along corresponding edges
    # ========================================================================
    if num_corresponding == 2:
        print(f"  Using two-corresponding-edge method")
        
        edge1_v1, edge1_v2 = corresponding_edges[0]
        edge2_v1, edge2_v2 = corresponding_edges[1]
        
        # Calculate edge lengths using helper function
        edge1_length = euclidean_distance(edge1_v1, edge1_v2)
        edge2_length = euclidean_distance(edge2_v1, edge2_v2)
        
        # Determine orientation: check if edges share a vertex with dir_v2
        # For proper pairing, both edges should "start" from the same end of the cell
        
        # Check which endpoint of edge1 is at or closest to dir_v2
        dist_e1v1_to_dirv2 = euclidean_distance(edge1_v1, dir_v2)
        dist_e1v2_to_dirv2 = euclidean_distance(edge1_v2, dir_v2)
        
        # If edge1_v1 is at dir_v2, keep orientation; if edge1_v2 is closer, reverse
        if dist_e1v1_to_dirv2 < 1e-6:
            # edge1_v1 is exactly at dir_v2, keep as is
            pass
        elif dist_e1v2_to_dirv2 < 1e-6:
            # edge1_v2 is exactly at dir_v2, reverse edge1
            edge1_v1, edge1_v2 = edge1_v2, edge1_v1
            print(f"  Reversed edge 1 to start from direction edge end")
        elif dist_e1v2_to_dirv2 < dist_e1v1_to_dirv2:
            # Neither is exact, but v2 is closer - reverse
            edge1_v1, edge1_v2 = edge1_v2, edge1_v1
            print(f"  Reversed edge 1 (endpoint closer to dir_v2)")
        
        # Check which endpoint of edge2 is at or closest to dir_v2 or dir_v1
        dist_e2v1_to_dirv2 = euclidean_distance(edge2_v1, dir_v2)
        dist_e2v2_to_dirv2 = euclidean_distance(edge2_v2, dir_v2)
        dist_e2v1_to_dirv1 = euclidean_distance(edge2_v1, dir_v1)
        dist_e2v2_to_dirv1 = euclidean_distance(edge2_v2, dir_v1)
        
        # For opposite-side edges: if edge2 connects to dir_v1 instead of dir_v2, reverse it
        if dist_e2v2_to_dirv1 < 1e-6:
            # edge2_v2 is at dir_v1 (opposite end), reverse so it conceptually "starts" from same side
            edge2_v1, edge2_v2 = edge2_v2, edge2_v1
            print(f"  Reversed edge 2 to align with edge 1 (opposite sides)")
        elif dist_e2v1_to_dirv1 < 1e-6:
            # edge2_v1 is at dir_v1, keep as is
            pass
        elif dist_e2v2_to_dirv2 < 1e-6:
            # edge2_v2 is at dir_v2, reverse to start from there
            edge2_v1, edge2_v2 = edge2_v2, edge2_v1
            print(f"  Reversed edge 2 to start from direction edge end")
        elif dist_e2v1_to_dirv2 < 1e-6:
            # edge2_v1 is at dir_v2, keep as is  
            pass
        elif dist_e2v2_to_dirv2 < dist_e2v1_to_dirv2:
            # Neither exact, but v2 closer to dir_v2
            edge2_v1, edge2_v2 = edge2_v2, edge2_v1
            print(f"  Reversed edge 2 (endpoint closer to dir_v2)")
        
        print(f"  Edge 1 length: {edge1_length:.2f} m")
        print(f"  Edge 2 length: {edge2_length:.2f} m")
        print(f"  Start offset: {start_offset:.2f} m (from direction edge end)")
        
        # Use the LONGER edge length to determine spacing for both edges
        # This ensures equal line spacing along the slicing direction
        max_edge_length = max(edge1_length, edge2_length)
        
        # Calculate number of points based on the longer edge
        available_length = max_edge_length - start_offset
        if available_length < 0:
            available_length = 0
        
        num_points = int(available_length / line_spacing) + 1
        
        # Generate points on BOTH edges using the SAME distances
        points1 = []
        points2 = []
        
        for i in range(num_points):
            distance = start_offset + i * line_spacing
            
            # Add small epsilon to avoid vertex tangency when distance is exactly 0
            if distance < 1e-6:
                distance = 1e-3  # 1mm offset to ensure line crosses into polygon
            
            # Point on edge 1 (clamp to edge length)
            if distance <= edge1_length:
                t1 = distance / edge1_length if edge1_length > 1e-10 else 0
                t1 = max(0.0, min(1.0, t1))
                px1 = edge1_v1[0] + t1 * (edge1_v2[0] - edge1_v1[0])
                py1 = edge1_v1[1] + t1 * (edge1_v2[1] - edge1_v1[1])
                points1.append((px1, py1))
            
            # Point on edge 2 (clamp to edge length)
            if distance <= edge2_length:
                t2 = distance / edge2_length if edge2_length > 1e-10 else 0
                t2 = max(0.0, min(1.0, t2))
                px2 = edge2_v1[0] + t2 * (edge2_v2[0] - edge2_v1[0])
                py2 = edge2_v1[1] + t2 * (edge2_v2[1] - edge2_v1[1])
                points2.append((px2, py2))
        
        # One-to-one pairing: connect corresponding points
        num_pairs = min(len(points1), len(points2))
        
        print(f"  Points on edge 1: {len(points1)}")
        print(f"  Points on edge 2: {len(points2)}")
        print(f"  Number of paired slicing lines: {num_pairs}")
        
        line_segments = []
        for i in range(num_pairs):
            line_segments.append((points1[i], points2[i]))
        
        # IMPROVED: Handle unpaired points as one-corresponding-edge case
        # Use the last slicing line direction and find intersections with other edges
        if len(points1) != len(points2):
            unpaired_count = abs(len(points1) - len(points2))
            print(f"  ⚠ {unpaired_count} point(s) unpaired - treating as one-corresponding-edge")
            
            # Determine which edge has more points
            if len(points1) > len(points2):
                longer_edge_points = points1
                longer_edge_v1 = edge1_v1
                longer_edge_v2 = edge1_v2
                unpaired_start_idx = len(points2)
                print(f"  Using remaining {unpaired_count} point(s) from edge 1")
            else:
                longer_edge_points = points2
                longer_edge_v1 = edge2_v1
                longer_edge_v2 = edge2_v2
                unpaired_start_idx = len(points1)
                print(f"  Using remaining {unpaired_count} point(s) from edge 2")
            
            # Get the direction from the last paired slicing line
            if num_pairs > 0:
                last_line_p1, last_line_p2 = line_segments[-1]
                slice_dx = last_line_p2[0] - last_line_p1[0]
                slice_dy = last_line_p2[1] - last_line_p1[1]
                slice_length = math.sqrt(slice_dx**2 + slice_dy**2)
                
                if slice_length > 1e-10:
                    slice_nx = slice_dx / slice_length
                    slice_ny = slice_dy / slice_length
                    
                    print(f"  Using last paired line direction: ({slice_nx:.4f}, {slice_ny:.4f})")
                    
                    # Process unpaired points
                    for i in range(unpaired_start_idx, len(longer_edge_points)):
                        px, py = longer_edge_points[i]
                        
                        # Create a line parallel to the last slicing line direction
                        margin = 1000  # Large number to ensure we cross the cell
                        line_start = (px - slice_nx * margin, py - slice_ny * margin)
                        line_end = (px + slice_nx * margin, py + slice_ny * margin)
                        
                        # Find intersections with cell polygon
                        intersections = []
                        n = len(cell)
                        
                        for j in range(n):
                            edge_v1 = cell[j]
                            edge_v2 = cell[(j + 1) % n]
                            
                            intersection = line_segment_intersection(line_start, line_end, edge_v1, edge_v2)
                            
                            if intersection is not None:
                                # Avoid duplicates
                                is_duplicate = False
                                for existing_int in intersections:
                                    dist = math.sqrt((intersection[0] - existing_int[0])**2 + 
                                                   (intersection[1] - existing_int[1])**2)
                                    if dist < 1e-6:
                                        is_duplicate = True
                                        break
                                
                                if not is_duplicate:
                                    intersections.append(intersection)
                        
                        # Use the two intersections to form a slicing line
                        if len(intersections) >= 2:
                            # Sort by distance from the starting point to maintain order
                            intersections.sort(key=lambda p: (p[0] - px)**2 + (p[1] - py)**2)
                            line_segments.append((intersections[0], intersections[1]))
                            print(f"    Unpaired point {i - unpaired_start_idx + 1}: found {len(intersections)} intersections → added line")
                        else:
                            print(f"    Unpaired point {i - unpaired_start_idx + 1}: only {len(intersections)} intersection(s) → skipped")
                else:
                    print(f"  ⚠ Last paired line has zero length, cannot determine direction")
            else:
                print(f"  ⚠ No paired lines exist, cannot process unpaired points")
        
        return line_segments
    
    # ========================================================================
    # SCENARIO 2: ONE CORRESPONDING EDGE
    # Generate points along corresponding edge, shoot rays parallel to direction
    # Start point: offset from the END of direction edge along corresponding edge
    # ========================================================================
    elif num_corresponding == 1:
        print(f"  Using one-corresponding-edge method")
        
        corr_v1, corr_v2 = corresponding_edges[0]
        
        # Calculate corresponding edge length using helper function
        corr_length = euclidean_distance(corr_v1, corr_v2)
        
        # Check which endpoint of corresponding edge connects to dir_v2 (end of direction edge)
        # Use exact matching with small tolerance instead of distance comparison
        dist_cv1_to_dirv2 = euclidean_distance(corr_v1, dir_v2)
        dist_cv2_to_dirv2 = euclidean_distance(corr_v2, dir_v2)
        dist_cv1_to_dirv1 = euclidean_distance(corr_v1, dir_v1)
        dist_cv2_to_dirv1 = euclidean_distance(corr_v2, dir_v1)
        
        # Determine edge orientation based on exact endpoint matching
        if dist_cv1_to_dirv2 < 1e-6:
            # corr_v1 matches dir_v2 (END) → edge is correctly oriented
            print(f"  Corresponding edge starts from direction edge END (correct orientation)")
        elif dist_cv2_to_dirv2 < 1e-6:
            # corr_v2 matches dir_v2 (END) → need to reverse
            corr_v1, corr_v2 = corr_v2, corr_v1
            print(f"  Reversed corresponding edge to start from direction edge END")
        elif dist_cv2_to_dirv1 < 1e-6:
            # corr_v2 matches dir_v1 (START) → opposite side, need to reverse to start from dir_v1
            corr_v1, corr_v2 = corr_v2, corr_v1
            print(f"  Reversed corresponding edge to start from direction edge START (opposite side)")
        elif dist_cv1_to_dirv1 < 1e-6:
            # corr_v1 matches dir_v1 (START) → opposite side, already correct orientation
            print(f"  Corresponding edge starts from direction edge START (opposite side)")
        else:
            # Fallback: use closest endpoint to dir_v2
            if dist_cv2_to_dirv2 < dist_cv1_to_dirv2:
                corr_v1, corr_v2 = corr_v2, corr_v1
                print(f"  Reversed corresponding edge based on closest endpoint to dir_v2 (fallback)")
            else:
                print(f"  Using corresponding edge as-is (fallback)")
        
        print(f"  Corresponding edge length: {corr_length:.2f} m")
        print(f"  Start offset: {start_offset:.2f} m (from end of direction edge)")
        
        # EXTENDED SLICING: Continue beyond corresponding edge until no intersections
        # Calculate corresponding edge direction vector
        corr_dx = corr_v2[0] - corr_v1[0]
        corr_dy = corr_v2[1] - corr_v1[1]
        
        # Generate points along corresponding edge direction (including extensions)
        line_segments = []
        distance = start_offset
        i = 0
        max_iterations = 1000  # Safety limit to prevent infinite loops
        
        while i < max_iterations:
            # Add small epsilon to avoid vertex tangency when distance is exactly 0
            effective_distance = distance
            if effective_distance < 1e-6:
                effective_distance = 1e-3  # 1mm offset to ensure line crosses into polygon
            
            # Calculate t parameter (can exceed 1.0 to go beyond edge)
            t = effective_distance / corr_length if corr_length > 1e-10 else 0
            
            # Point along corresponding edge direction (no clamping - allow extension)
            px = corr_v1[0] + t * corr_dx
            py = corr_v1[1] + t * corr_dy
            
            # Create a line parallel to direction edge passing through this point
            margin = 1000  # Large number to ensure we cross the cell
            line_start = (px - dir_nx * margin, py - dir_ny * margin)
            line_end = (px + dir_nx * margin, py + dir_ny * margin)
            
            # Find intersections with cell polygon
            intersections = []
            n = len(cell)
            
            for j in range(n):
                edge_v1 = cell[j]
                edge_v2 = cell[(j + 1) % n]
                
                intersection = line_segment_intersection(line_start, line_end, edge_v1, edge_v2)
                
                if intersection is not None:
                    # Avoid duplicates
                    is_duplicate = False
                    for existing_int in intersections:
                        dist = math.sqrt((intersection[0] - existing_int[0])**2 + 
                                       (intersection[1] - existing_int[1])**2)
                        if dist < 1e-6:
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        intersections.append(intersection)
            
            # Check if we still have valid intersections
            if len(intersections) < 2:
                # No more valid slicing lines - stop
                break
            
            # Sort intersections along the direction vector
            intersections_with_proj = []
            for int_pt in intersections:
                proj = (int_pt[0] - px) * dir_nx + (int_pt[1] - py) * dir_ny
                intersections_with_proj.append((proj, int_pt))
            
            intersections_with_proj.sort(key=lambda x: x[0])
            
            # Create line segments from pairs
            sorted_intersections = [pt for _, pt in intersections_with_proj]
            for j in range(0, len(sorted_intersections) - 1, 2):
                if j + 1 < len(sorted_intersections):
                    line_segments.append((sorted_intersections[j], sorted_intersections[j + 1]))
            
            # Move to next position
            distance += line_spacing
            i += 1
        
        print(f"  Generated {len(line_segments)} slicing lines (extended beyond edge)")
        
        return line_segments
    
    # ========================================================================
    # SCENARIO 3: NO CORRESPONDING EDGES
    # Perpendicular slicing from direction edge
    # Start point: perpendicular offset from the direction edge
    # ========================================================================
    else:
        print(f"  Using perpendicular slicing method (no corresponding edges)")
        
        # Calculate rotation to make direction edge vertical
        edge_angle = math.atan2(dir_dy, dir_dx)
        rotation_angle = math.pi / 2 - edge_angle
        
        cos_theta = math.cos(rotation_angle)
        sin_theta = math.sin(rotation_angle)
        
        # Rotate cell vertices
        rotated_cell = []
        for vertex in cell:
            x_rot = vertex[0] * cos_theta - vertex[1] * sin_theta
            y_rot = vertex[0] * sin_theta + vertex[1] * cos_theta
            rotated_cell.append((x_rot, y_rot))
        
        # Rotate direction edge endpoints to determine which end to reference
        dir_v1_rot = (dir_v1[0] * cos_theta - dir_v1[1] * sin_theta,
                      dir_v1[0] * sin_theta + dir_v1[1] * cos_theta)
        dir_v2_rot = (dir_v2[0] * cos_theta - dir_v2[1] * sin_theta,
                      dir_v2[0] * sin_theta + dir_v2[1] * cos_theta)
        
        # Translate so direction edge END (dir_v2) is at x=0
        # This ensures start_offset is measured from the end of the direction edge
        translation_x = -dir_v2_rot[0]
        
        translated_cell = []
        for x, y in rotated_cell:
            translated_cell.append((x + translation_x, y))
        
        # Find bounds
        x_coords = [vertex[0] for vertex in translated_cell]
        min_x = min(x_coords)
        max_x = max(x_coords)
        
        print(f"  Transformed cell bounds: X=[{min_x:.2f}, {max_x:.2f}]")
        print(f"  Direction edge END at x=0.00")
        print(f"  Start offset: {start_offset:.2f} m (perpendicular from direction edge end)")
        
        # Determine sweep direction and generate lines
        # Start from start_offset perpendicular to the direction edge
        # Add small epsilon to avoid vertex tangency when start_offset is exactly 0
        effective_start_offset = start_offset
        if effective_start_offset < 1e-6:
            effective_start_offset = 1e-3  # 1mm offset to ensure line crosses into polygon
        
        if abs(max_x) > abs(min_x):
            sweep_start = effective_start_offset
            sweep_end = max_x
            sweep_increment = line_spacing
        else:
            sweep_start = -effective_start_offset
            sweep_end = min_x
            sweep_increment = -line_spacing
        
        line_segments_transformed = []
        current_x = sweep_start
        
        if sweep_increment > 0:
            while current_x <= sweep_end:
                y_coords = [vertex[1] for vertex in translated_cell]
                min_y = min(y_coords)
                max_y = max(y_coords)
                margin = (max_y - min_y) * 2
                
                line_start = (current_x, min_y - margin)
                line_end = (current_x, max_y + margin)
                
                intersections = []
                n = len(translated_cell)
                
                for i in range(n):
                    edge_v1 = translated_cell[i]
                    edge_v2 = translated_cell[(i + 1) % n]
                    
                    intersection = line_segment_intersection(line_start, line_end, edge_v1, edge_v2)
                    
                    if intersection is not None:
                        is_duplicate = False
                        for existing_int in intersections:
                            dist = math.sqrt((intersection[0] - existing_int[0])**2 + 
                                           (intersection[1] - existing_int[1])**2)
                            if dist < 1e-6:
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            intersections.append(intersection)
                
                intersections.sort(key=lambda p: p[1])
                
                for j in range(0, len(intersections) - 1, 2):
                    if j + 1 < len(intersections):
                        segment = (intersections[j], intersections[j + 1])
                        line_segments_transformed.append(segment)
                
                current_x += line_spacing
        else:
            while current_x >= sweep_end:
                y_coords = [vertex[1] for vertex in translated_cell]
                min_y = min(y_coords)
                max_y = max(y_coords)
                margin = (max_y - min_y) * 2
                
                line_start = (current_x, min_y - margin)
                line_end = (current_x, max_y + margin)
                
                intersections = []
                n = len(translated_cell)
                
                for i in range(n):
                    edge_v1 = translated_cell[i]
                    edge_v2 = translated_cell[(i + 1) % n]
                    
                    intersection = line_segment_intersection(line_start, line_end, edge_v1, edge_v2)
                    
                    if intersection is not None:
                        is_duplicate = False
                        for existing_int in intersections:
                            dist = math.sqrt((intersection[0] - existing_int[0])**2 + 
                                           (intersection[1] - existing_int[1])**2)
                            if dist < 1e-6:
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            intersections.append(intersection)
                
                intersections.sort(key=lambda p: p[1])
                
                for j in range(0, len(intersections) - 1, 2):
                    if j + 1 < len(intersections):
                        segment = (intersections[j], intersections[j + 1])
                        line_segments_transformed.append(segment)
                
                current_x -= line_spacing
        
        # Transform back to original coordinates
        line_segments_original = []
        inv_cos_theta = math.cos(-rotation_angle)
        inv_sin_theta = math.sin(-rotation_angle)
        
        for seg_start, seg_end in line_segments_transformed:
            # Reverse translation
            p1_x = seg_start[0] - translation_x
            p1_y = seg_start[1]
            p2_x = seg_end[0] - translation_x
            p2_y = seg_end[1]
            
            # Reverse rotation
            p1_orig_x = p1_x * inv_cos_theta - p1_y * inv_sin_theta
            p1_orig_y = p1_x * inv_sin_theta + p1_y * inv_cos_theta
            p2_orig_x = p2_x * inv_cos_theta - p2_y * inv_sin_theta
            p2_orig_y = p2_x * inv_sin_theta + p2_y * inv_cos_theta
            
            line_segments_original.append(((p1_orig_x, p1_orig_y), (p2_orig_x, p2_orig_y)))
        
        return line_segments_original
    

# ============================================================================
# SECTION 5: SURVEY GRID GENERATION CORE
# Main algorithm: implements Mission Planner's survey grid strategy
# ============================================================================
def generate_survey_grid(polygon_m, altitude, hfov, vfov, lateral_overlap, grid_angle=None):
    """
    Generate survey grid waypoints using Mission Planner's algorithm.
    
    Args:
        polygon_m: polygon vertices in meters [(x, y), ...]
        altitude: flight altitude in meters
        hfov, vfov: camera field of view in degrees
        lateral_overlap: side overlap percentage
        grid_angle: grid orientation in degrees (None = auto-detect)
        
    Returns: list of waypoints [(x, y, alt), ...]
    """

    # Save original polygon for validation (before any subdivision adds new points)
    original_polygon = polygon_m.copy()

    # Decompose polygon into polyline segments using an adaptive angular threshold
    # We iterate through angles from large value down to 0 until we can decompose 
    # the polygon into ~4 polylines (or 3 for triangles).
    polylines, threshold_used = adaptive_polyline_decomposition(polygon_m, target_polylines=4)
    
    print(f"\nDecomposed into {len(polylines)} polylines:")
    for i, polyline_indices in enumerate(polylines):
        print(f"  Polyline {i+1}: vertices {polyline_indices}")

    print("\n" + "="*60)
    print("GENERATING SURVEY GRID")
    print("="*60)

    # Calculate the length of each polyline and sort them by length (longest first)
    polyline_lengths = []
    for i, polyline_indices in enumerate(polylines):
        # Calculate total length using helper function
        length = polyline_length(polyline_indices, polygon_m)
        polyline_lengths.append((i, length, polyline_indices))
    
    # Sort by length (descending order - longest first)
    polyline_lengths.sort(key=lambda x: x[1], reverse=True)
    
    # Reorder polylines so polyline 1 is the longest
    sorted_polylines = [item[2] for item in polyline_lengths]
    
    print(f"\nPolylines sorted by length (longest first):")
    for i, (orig_idx, length, indices) in enumerate(polyline_lengths):
        print(f"  Polyline {i+1}: length = {length:.2f} m, vertices {indices} (original #{orig_idx+1})")
    
    # Update polylines to be the sorted version
    polylines = sorted_polylines

    # Define heading and following polylines based on adjacency to the longest polyline
    # 
    # Following polylines: Polylines that define the main survey direction
    #   - For 4 polylines: Longest polyline + the opposite (non-adjacent) polyline
    #   - For 3 polylines: Only the longest polyline
    #
    # Heading polylines: Polylines perpendicular to the survey direction
    #   - For 4 polylines: The two polylines adjacent to the longest one
    #   - For 3 polylines: The two polylines adjacent to the longest one
    
    following_polylines = []
    heading_polylines = []
    
    if len(polylines) >= 3:
        # The longest polyline is always first (already sorted)
        longest_polyline = polylines[0]
        following_polylines.append(0)  # Index of longest polyline
        
        # Find which polylines are adjacent to the longest one
        # Two polylines are adjacent if they share a vertex
        longest_vertices = set(longest_polyline)
        adjacent_indices = []
        non_adjacent_indices = []
        
        for i in range(1, len(polylines)):
            polyline_vertices = set(polylines[i])
            # Check if they share any vertices
            if longest_vertices & polyline_vertices:  # Set intersection
                adjacent_indices.append(i)
            else:
                non_adjacent_indices.append(i)
        
        # Classify polylines based on count
        if len(polylines) == 4:
            # Rectangle case: longest + opposite are following, two adjacent are heading
            heading_polylines = adjacent_indices
            following_polylines.extend(non_adjacent_indices)
        elif len(polylines) == 3:
            # Triangle case: longest is following, two adjacent are heading
            heading_polylines = adjacent_indices
        else:
            # General case: longest is following, all others are heading
            heading_polylines = list(range(1, len(polylines)))
        
        print(f"\nPolyline classification:")
        print(f"  Following polylines (survey direction): {following_polylines}")
        print(f"    {[f'Polyline {i+1}' for i in following_polylines]}")
        print(f"  Heading polylines (perpendicular): {heading_polylines}")
        print(f"    {[f'Polyline {i+1}' for i in heading_polylines]}")
    else:
        # Less than 3 polylines - use all as following
        following_polylines = list(range(len(polylines)))
        print(f"\nPolyline classification:")
        print(f"  Following polylines: {following_polylines} (insufficient polylines for heading detection)")


    # Equalize point counts on following polylines for optimal pairing
    # For rectangular survey areas (4 polylines), the two following polylines should have
    # equal numbers of points so that survey lines can be generated between corresponding
    # point pairs. If one following polyline has fewer points, we insert additional points
    # at locations that minimize the maximum distance between corresponding point pairs.
    #
    # Algorithm:
    #   1. Identify polyline A (more points) and polyline B (fewer points)
    #   2. For each point in A, find its nearest point in B and compute distance
    #   3. Select the N points in A with the longest distances (poorly matched points)
    #   4. For each selected point (target point):
    #      - Draw perpendicular lines from target point to each edge in B
    #      - Find the intersection with shortest distance
    #      - Insert new point at that intersection
    
    if len(polylines) == 4 and len(following_polylines) == 2:
        print(f"\nEqualizing points on following polylines...")
        
        # Get the two following polylines
        following_idx_1 = following_polylines[0]
        following_idx_2 = following_polylines[1]
        
        polyline_1_indices = polylines[following_idx_1]
        polyline_2_indices = polylines[following_idx_2]
        
        num_points_1 = len(polyline_1_indices)
        num_points_2 = len(polyline_2_indices)
        
        print(f"  Following polyline {following_idx_1 + 1}: {num_points_1} points")
        print(f"  Following polyline {following_idx_2 + 1}: {num_points_2} points")
        
        if num_points_1 != num_points_2:
            # Determine which polyline has more points (A) and fewer points (B)
            if num_points_1 > num_points_2:
                polyline_A_idx = following_idx_1
                polyline_A_indices = polyline_1_indices
                polyline_B_idx = following_idx_2
                polyline_B_indices = polyline_2_indices
            else:
                polyline_A_idx = following_idx_2
                polyline_A_indices = polyline_2_indices
                polyline_B_idx = following_idx_1
                polyline_B_indices = polyline_1_indices
            
            num_new_points = len(polyline_A_indices) - len(polyline_B_indices)
            
            print(f"  Polyline A (more points): Polyline {polyline_A_idx + 1} with {len(polyline_A_indices)} points")
            print(f"  Polyline B (fewer points): Polyline {polyline_B_idx + 1} with {len(polyline_B_indices)} points")
            print(f"  Need to insert {num_new_points} new points in B")
            
            # Step 1: For each point in A (excluding endpoints), find nearest point in B and compute distance
            point_distances = []
            for i, idx_A in enumerate(polyline_A_indices):
                # Skip the first and last points (endpoints of the polyline)
                if i == 0 or i == len(polyline_A_indices) - 1:
                    continue
                
                point_A = polygon_m[idx_A]
                
                # Find nearest point in B
                min_dist = float('inf')
                for idx_B in polyline_B_indices:
                    point_B = polygon_m[idx_B]
                    dist = euclidean_distance(point_A, point_B)
                    if dist < min_dist:
                        min_dist = dist
                
                point_distances.append((i, idx_A, min_dist, point_A))
            
            # Step 2: Sort by distance (descending) and select top N points
            point_distances.sort(key=lambda x: x[2], reverse=True)
            target_points = point_distances[:num_new_points]
            
            print(f"  Selected {len(target_points)} target points with longest distances:")
            for i, (idx_in_A, idx_A, dist, point_A) in enumerate(target_points):
                print(f"    Target {i+1}: point {idx_in_A} at {point_A}, distance = {dist:.2f} m")
            
            # Step 3: For each target point, find optimal insertion location in B
            new_points_to_insert = []
            
            for idx_in_A, idx_A, _, target_point in target_points:
                best_insertion = None
                best_distance = float('inf')
                best_edge_idx = -1
                
                # Check each edge in B
                for i in range(len(polyline_B_indices) - 1):
                    edge_start_idx = polyline_B_indices[i]
                    edge_end_idx = polyline_B_indices[i + 1]
                    edge_start = polygon_m[edge_start_idx]
                    edge_end = polygon_m[edge_end_idx]
                    
                    # Edge vector
                    edge_dx = edge_end[0] - edge_start[0]
                    edge_dy = edge_end[1] - edge_start[1]
                    edge_length_sq = edge_dx**2 + edge_dy**2
                    
                    if edge_length_sq < 1e-10:
                        continue  # Skip degenerate edge
                    
                    # Vector from edge start to target point
                    to_target_dx = target_point[0] - edge_start[0]
                    to_target_dy = target_point[1] - edge_start[1]
                    
                    # Project target point onto edge (parameterized by t in [0, 1])
                    t = (to_target_dx * edge_dx + to_target_dy * edge_dy) / edge_length_sq
                    
                    # Clamp t to [0, 1] to stay on the edge segment
                    t = max(0.0, min(1.0, t))
                    
                    # Find the perpendicular projection point
                    projection_x = edge_start[0] + t * edge_dx
                    projection_y = edge_start[1] + t * edge_dy
                    
                    # Calculate distance from target point to projection
                    dist = math.sqrt((target_point[0] - projection_x)**2 + 
                                   (target_point[1] - projection_y)**2)
                    
                    # Track the closest projection
                    if dist < best_distance:
                        best_distance = dist
                        best_insertion = (projection_x, projection_y)
                        best_edge_idx = i
                
                if best_insertion is not None:
                    new_points_to_insert.append((best_edge_idx, best_insertion, best_distance))
                    print(f"    → Insert at edge {best_edge_idx} ({best_insertion[0]:.2f}, {best_insertion[1]:.2f}), distance = {best_distance:.2f} m")
            
            # Step 4: Insert new points into polyline B
            # Sort by edge index (descending) to insert from end to beginning
            new_points_to_insert.sort(key=lambda x: x[0], reverse=True)
            
            # Build new polyline B with inserted points
            new_polyline_B = []
            
            # Group insertions by edge
            insertions_by_edge = {}
            for edge_idx, point, _ in new_points_to_insert:
                if edge_idx not in insertions_by_edge:
                    insertions_by_edge[edge_idx] = []
                insertions_by_edge[edge_idx].append(point)
            
            # For each edge with insertions, sort them by distance along the edge
            for edge_idx in insertions_by_edge:
                edge_start = polygon_m[polyline_B_indices[edge_idx]]
                points = insertions_by_edge[edge_idx]
                
                # Sort by distance from edge start
                points.sort(key=lambda p: (p[0] - edge_start[0])**2 + (p[1] - edge_start[1])**2)
                insertions_by_edge[edge_idx] = points
            
            # Reconstruct polyline B with insertions
            for i in range(len(polyline_B_indices)):
                # Add original vertex
                new_polyline_B.append(polyline_B_indices[i])
                
                # If this is the start of an edge with insertions, add them
                if i < len(polyline_B_indices) - 1 and i in insertions_by_edge:
                    for new_point in insertions_by_edge[i]:
                        # Add new point to polygon_m
                        polygon_m.append(new_point)
                        new_point_idx = len(polygon_m) - 1
                        new_polyline_B.append(new_point_idx)
            
            # Update polyline B in the polylines list
            polylines[polyline_B_idx] = new_polyline_B
            
            print(f"  ✓ Subdivision complete: {len(new_polyline_B)} points")
            print(f"    Added {len(new_polyline_B) - len(polyline_B_indices)} new vertices to polygon")
        else:
            print(f"  ✓ Point counts already equal ({num_points_1} points each)")


    # Create corresponding pairs of waypoints between the two following polylines
    # For rectangular survey areas (4 polylines), we pair interior points in reverse order
    # because the UAV moves from one heading polyline to the other.
    #
    # Example: Following polyline 1: A1, A2, A3, A4, A5
    #          Following polyline 2: B1, B2, B3, B4, B5
    #
    # A1 and B1 are endpoints (shared with heading polylines) - NOT paired
    # A5 and B5 are endpoints (shared with heading polylines) - NOT paired
    # Interior points paired in reverse: A2↔B4, A3↔B3, A4↔B2
    #
    # To determine the correct order, we check which heading polyline connects to which end
    
    corresponding_pairs = []
    
    if len(polylines) == 4 and len(following_polylines) == 2:
        print(f"\n{'='*60}")
        print("CREATING CORRESPONDING PAIRS")
        print(f"{'='*60}")
        
        # Get the two following polylines
        following_idx_1 = following_polylines[0]
        following_idx_2 = following_polylines[1]
        
        polyline_1_indices = polylines[following_idx_1]
        polyline_2_indices = polylines[following_idx_2]
        
        # For cell generation, we need to pair ALL points to define cell boundaries
        # But we'll create one pair per SEGMENT (between consecutive points)
        # For n points, we have (n-1) segments, which creates (n-1) cells
        #
        # Example with 4 points [A, B, C, D] on each following polyline:
        #   - Segment 1: A-B creates cell 1 bounded by pairs at A and B
        #   - Segment 2: B-C creates cell 2 bounded by pairs at B and C
        #   - Segment 3: C-D creates cell 3 bounded by pairs at C and D
        #
        # So we create a corresponding pair at EACH point to define cell boundaries
        
        all_points_1 = polyline_1_indices
        all_points_2 = polyline_2_indices
        
        print(f"\nFollowing polyline {following_idx_1 + 1}: {len(polyline_1_indices)} points")
        print(f"Following polyline {following_idx_2 + 1}: {len(polyline_2_indices)} points")
        
        if len(all_points_1) > 0 and len(all_points_2) > 0:
            # Determine pairing order by checking edge continuity
            # Check if first points or last points are connected by a heading polyline
            
            # Get endpoints
            first_1 = polyline_1_indices[0]
            last_1 = polyline_1_indices[-1]
            first_2 = polyline_2_indices[0]
            last_2 = polyline_2_indices[-1]
            
            # Check which heading polylines connect which endpoints
            # Two endpoints are connected if they share an edge (consecutive in a heading polyline)
            first_first_connected = False  # first_1 and first_2
            first_last_connected = False   # first_1 and last_2
            
            for heading_idx in heading_polylines:
                heading_polyline = polylines[heading_idx]
                # Check if this heading polyline connects the endpoints
                if first_1 in heading_polyline and first_2 in heading_polyline:
                    # Check if they're consecutive
                    idx1 = heading_polyline.index(first_1)
                    idx2 = heading_polyline.index(first_2)
                    if abs(idx1 - idx2) == 1:
                        first_first_connected = True
                
                if first_1 in heading_polyline and last_2 in heading_polyline:
                    idx1 = heading_polyline.index(first_1)
                    idx2 = heading_polyline.index(last_2)
                    if abs(idx1 - idx2) == 1:
                        first_last_connected = True
            
            # Determine pairing order based on connectivity
            if first_first_connected:
                # first_1 connects to first_2 → pair in same order
                pairs_list_2 = all_points_2
                print(f"\n  Pairing order: SAME direction (first-to-first connected)")
            elif first_last_connected:
                # first_1 connects to last_2 → pair in reverse order
                pairs_list_2 = list(reversed(all_points_2))
                print(f"\n  Pairing order: REVERSE direction (first-to-last connected)")
            else:
                # Default: assume reverse pairing (most common for survey grids)
                pairs_list_2 = list(reversed(all_points_2))
                print(f"\n  Pairing order: REVERSE direction (default)")
            
            # Create pairs for ALL points
            # Each pair defines a cell boundary
            # Number of pairs = number of points
            # Number of cells = number of points - 1 (cells are between pairs)
            
            num_pairs = min(len(all_points_1), len(all_points_2))
            print(f"\n  Creating {num_pairs} corresponding pairs (will create {num_pairs-1} cells between them)")
            
            for i in range(num_pairs):
                idx_1 = all_points_1[i]
                idx_2 = pairs_list_2[i]
                
                point_1 = polygon_m[idx_1]
                point_2 = polygon_m[idx_2]
                
                distance = math.sqrt((point_2[0] - point_1[0])**2 + 
                                   (point_2[1] - point_1[1])**2)
                
                # Validate cell: For a cell to be valid, check if:
                # 1. Neither point is an endpoint of any polyline
                # 2. The line connecting the two points doesn't exit the polygon (stays inside)
                
                midpoint_x = (point_1[0] + point_2[0]) / 2
                midpoint_y = (point_1[1] + point_2[1]) / 2
                
                # Check 1: Exclude pairs where either point is an endpoint of any polyline
                is_endpoint_pair = False
                
                for poly_idx, polyline_indices in enumerate(polylines):
                    # Check if idx_1 or idx_2 is an endpoint (first or last vertex) of this polyline
                    if len(polyline_indices) > 0:
                        first_vertex = polyline_indices[0]
                        last_vertex = polyline_indices[-1]
                        
                        if idx_1 == first_vertex or idx_1 == last_vertex or idx_2 == first_vertex or idx_2 == last_vertex:
                            is_endpoint_pair = True
                            print(f"    ⚠ Pair {i} rejected: vertex {idx_1} or {idx_2} is endpoint of polyline {poly_idx + 1}")
                            break
                
                if is_endpoint_pair:
                    continue  # Skip this pair
                
                # Check 2: Sample multiple points along the line to ensure it stays inside
                valid = True
                for t in [0.25, 0.5, 0.75]:
                    test_x = point_1[0] + t * (point_2[0] - point_1[0])
                    test_y = point_1[1] + t * (point_2[1] - point_1[1])
                    if not point_in_polygon((test_x, test_y), original_polygon):
                        valid = False
                        print(f"    ⚠ Pair {i} rejected: point at t={t} ({test_x:.2f}, {test_y:.2f}) outside polygon")
                        break
                
                # Only add pair if it passes both validation checks
                if valid:
                    corresponding_pairs.append({
                        'polyline_1_idx': following_idx_1,
                        'polyline_2_idx': following_idx_2,
                        'point_1_idx': idx_1,
                        'point_2_idx': idx_2,
                        'point_1': point_1,
                        'point_2': point_2,
                        'distance': distance,
                        'pair_number': len(corresponding_pairs)  # Use actual count, not i
                    })
                    print(f"    ✓ Pair {len(corresponding_pairs)-1}: Point[{i}] ↔ Point[{pairs_list_2.index(idx_2)}], midpoint=({midpoint_x:.2f}, {midpoint_y:.2f}) inside polygon")
            
            # Display statistics
            if len(corresponding_pairs) > 0:
                distances = [pair['distance'] for pair in corresponding_pairs]
                avg_distance = sum(distances) / len(distances)
                min_distance = min(distances)
                max_distance = max(distances)
                
                print(f"\n  Pair statistics:")
                print(f"    Total pairs: {len(corresponding_pairs)}")
                print(f"    Average distance: {avg_distance:.2f} m")
                print(f"    Min distance: {min_distance:.2f} m")
                print(f"    Max distance: {max_distance:.2f} m")
                print(f"    Distance variation: {max_distance - min_distance:.2f} m")
                
                # Show first few pairs
                print(f"\n  Sample pairs (polyline 1 ↔ polyline 2):")
                for i in range(min(3, len(corresponding_pairs))):
                    pair = corresponding_pairs[i]
                    p1_pos = polyline_1_indices.index(pair['point_1_idx'])
                    p2_pos = polyline_2_indices.index(pair['point_2_idx'])
                    print(f"    Pair {i}: Point[{p1_pos}] ↔ Point[{p2_pos}], distance = {pair['distance']:.2f} m")
        else:
            print(f"\n  ⚠ Not enough points to create pairs")
        
        print(f"{'='*60}\n")
  
    # Calculate line spacing
    spacing = calculate_line_spacing(altitude, hfov, lateral_overlap)
    print(f"Line spacing: {spacing:.2f} m")

    # ========================================================================
    # CONNECTIVITY-BASED RECURSIVE CELL DECOMPOSITION
    # ========================================================================
    # We decompose the polygon into cells using a connectivity-based approach:
    # 1. Build connectivity graph of all points (original + inserted)
    # 2. Find clockwise traversal of polygon boundary
    # 3. Start from first point of longest polyline (deterministic)
    # 4. Use corresponding pairs to recursively cut polygon into cells
    # 5. Rebuild connectivity after each cut
    
    cells = []
    
    if len(corresponding_pairs) > 0:
        print(f"\n{'='*60}")
        print("CONNECTIVITY-BASED RECURSIVE CELL DECOMPOSITION")
        print(f"{'='*60}\n")
        
        # STEP 1: Build connectivity graph
        print("Step 1: Building connectivity graph")
        adjacency = build_connectivity_graph(polygon_m, polylines)
        
        print(f"  Adjacency graph ({len(adjacency)} vertices):")
        for vertex_idx in sorted(adjacency.keys()):
            if len(adjacency[vertex_idx]) > 0:
                print(f"    Vertex {vertex_idx}: → {adjacency[vertex_idx]}")
        
        # STEP 2: Find deterministic starting point (first vertex of longest polyline)
        print(f"\nStep 2: Finding deterministic starting point")
        start_vertex = find_longest_polyline_start(polylines, polygon_m)
        print(f"  Longest polyline starts at vertex {start_vertex}")
        
        # STEP 3: Traverse boundary in clockwise order from start
        print(f"\nStep 3: Traversing polygon boundary clockwise")
        boundary_order = find_clockwise_boundary(adjacency, start_vertex)
        print(f"  Boundary order ({len(boundary_order)} vertices): {boundary_order}")
        
        # STEP 4: Sort pairs by their position along boundary
        print(f"\nStep 4: Sorting {len(corresponding_pairs)} pairs by boundary position")
        
        # Map vertex index to boundary position
        vertex_to_boundary_pos = {v: i for i, v in enumerate(boundary_order)}
        
        sorted_pairs = sorted(corresponding_pairs, 
                             key=lambda p: vertex_to_boundary_pos.get(p['point_1_idx'], 999))
        
        for i, pair in enumerate(sorted_pairs):
            p1_pos = vertex_to_boundary_pos.get(pair['point_1_idx'], -1)
            p2_pos = vertex_to_boundary_pos.get(pair['point_2_idx'], -1)
            print(f"  Pair {i}: vertices {pair['point_1_idx']}↔{pair['point_2_idx']}, " +
                  f"boundary pos {p1_pos}↔{p2_pos}")
        
        # STEP 5: Recursively decompose
        print(f"\nStep 5: Recursive cell decomposition")
        print(f"{'='*60}\n")
        
        decompose_cell_recursive(polygon_m, polylines, sorted_pairs, 
                                adjacency, boundary_order, cells, depth=0)
        
        print(f"{'='*60}")
        print(f"✓ Created {len(cells)} cells from recursive decomposition")
        print(f"{'='*60}\n")
        
    else:
        # No pairs: entire polygon is one cell
        cells = [original_polygon.copy()]
        print(f"\n✓ No corresponding pairs - polygon is single cell\n")

    # ========================================================================
    # CELL EDGE LABELING
    # ========================================================================
    print(f"\n{'='*60}")
    print("LABELING CELL EDGES")
    print(f"{'='*60}\n")
    
    # Create data structure for labeled cell edges
    # Each cell will have a list of edges with their labels
    # Label types:
    #   1 = heading edge (on heading polylines)
    #   2 = direction edge (on longest polyline - the following polylines)
    #   3 = corresponding edge (on corresponding pairs)
    #   4 = other edges
    
    cell_edges_labeled = []
    
    # Build lists of edges for each category
    # 1. Heading edges (from heading polylines)
    heading_edges = []
    for hp_idx in heading_polylines:
        hp_verts = polylines[hp_idx]
        for i in range(len(hp_verts) - 1):
            v1 = polygon_m[hp_verts[i]]
            v2 = polygon_m[hp_verts[i + 1]]
            heading_edges.append((v1, v2))
    
    # 2. Direction edges (from LONGEST polyline only, not all following polylines)
    # The longest polyline is always polylines[0] (sorted by length)
    direction_edges = []
    longest_polyline_idx = 0
    longest_verts = polylines[longest_polyline_idx]
    for i in range(len(longest_verts) - 1):
        v1 = polygon_m[longest_verts[i]]
        v2 = polygon_m[longest_verts[i + 1]]
        direction_edges.append((v1, v2))
    
    # 3. Corresponding edges (from corresponding pairs)
    corresponding_edges = []
    for pair in corresponding_pairs:
        v1 = polygon_m[pair['point_1_idx']]
        v2 = polygon_m[pair['point_2_idx']]
        corresponding_edges.append((v1, v2))
    
    print(f"Edge categories:")
    print(f"  Heading edges: {len(heading_edges)} (from {len(heading_polylines)} heading polylines)")
    print(f"  Direction edges: {len(direction_edges)} (from longest polyline only)")
    print(f"  Corresponding edges: {len(corresponding_edges)} (from {len(corresponding_pairs)} pairs)")
    
    # Label edges for each cell
    for cell_idx, cell_vertices in enumerate(cells):
        print(f"\nCell {cell_idx}: {len(cell_vertices)} vertices")
        
        labeled_edges = []
        
        # Get all edges of this cell
        for i in range(len(cell_vertices)):
            v1 = cell_vertices[i]
            v2 = cell_vertices[(i + 1) % len(cell_vertices)]
            
            # Determine label for this edge
            label = 4  # Default: other
            label_name = "other"
            
            # Check if it's a heading edge (priority 1)
            for h_edge in heading_edges:
                if edge_matches(v1, v2, h_edge[0], h_edge[1]):
                    label = 1
                    label_name = "heading"
                    break
            
            # Check if it's a direction edge (priority 2)
            if label == 4:  # Only check if not already labeled
                for d_edge in direction_edges:
                    if edge_matches(v1, v2, d_edge[0], d_edge[1]):
                        label = 2
                        label_name = "direction"
                        break
            
            # Check if it's a corresponding edge (priority 3)
            if label == 4:  # Only check if not already labeled
                for c_edge in corresponding_edges:
                    if edge_matches(v1, v2, c_edge[0], c_edge[1]):
                        label = 3
                        label_name = "corresponding"
                        break
            
            labeled_edges.append({
                'v1': v1,
                'v2': v2,
                'label': label,
                'label_name': label_name
            })
            
            print(f"  Edge {i}: ({v1[0]:.1f},{v1[1]:.1f}) → ({v2[0]:.1f},{v2[1]:.1f}) = {label} ({label_name})")
        
        cell_edges_labeled.append(labeled_edges)
    
    print(f"\n✓ Labeled edges for {len(cell_edges_labeled)} cells")
    print(f"{'='*60}\n")



    # ========================================================================
    # GENERATE SLICING LINES FOR ALL CELLS
    # ========================================================================
    print(f"\n{'='*60}")
    print("GENERATING SLICING LINES FOR ALL CELLS")
    print(f"{'='*60}\n")
    
    # Parameters for slicing
    start_offset = 0.0  # Distance from direction edge to start slicing (meters)
    # spacing is already calculated above
    
    print(f"Slicing parameters:")
    print(f"  Line spacing: {spacing:.2f} m")
    print(f"  Start offset: {start_offset:.2f} m")
    print()
    
    # Generate slicing lines for each cell
    all_slicing_lines = []
    
    for cell_idx, (cell_vertices, labeled_edges) in enumerate(zip(cells, cell_edges_labeled)):
        print(f"\n{'='*60}")
        print(f"SLICING CELL {cell_idx}")
        print(f"{'='*60}")
        print(f"Cell vertices: {len(cell_vertices)} points")
        
        # Convert labeled edges to the format expected by slice_cell_with_lines
        # Format: list of (v1, v2, label) tuples
        edge_labels = []
        for edge in labeled_edges:
            edge_labels.append((edge['v1'], edge['v2'], edge['label']))
        
        # Call slice_cell_with_lines
        slicing_lines = slice_cell_with_lines(
            cell_vertices, 
            edge_labels, 
            start_offset, 
            spacing
        )
        
        print(f"\n✓ Generated {len(slicing_lines)} slicing line segments for Cell {cell_idx}")
        
        # Store slicing lines with cell index for reference
        all_slicing_lines.append({
            'cell_idx': cell_idx,
            'lines': slicing_lines,
            'num_lines': len(slicing_lines)
        })
    
    print(f"\n{'='*60}")
    print(f"SLICING SUMMARY")
    print(f"{'='*60}")
    total_lines = sum(cell_data['num_lines'] for cell_data in all_slicing_lines)
    print(f"Total cells sliced: {len(all_slicing_lines)}")
    print(f"Total slicing line segments: {total_lines}")
    for cell_data in all_slicing_lines:
        print(f"  Cell {cell_data['cell_idx']}: {cell_data['num_lines']} line segments")
    print(f"{'='*60}\n")

    # ========================================================================
    # LAWNMOWER LINE GENERATION FROM SLICING LINES
    # ========================================================================
    print(f"\n{'='*60}")
    print("GENERATING LAWNMOWER LINES FROM SLICING LINES")
    print(f"{'='*60}\n")
    
    
    lawnmower_lines = []  # List of lawnmower lines, each is a list of connected line segments
    
    if total_lines == 0:
        print("No slicing lines generated, skipping lawnmower line generation")
        return waypoints_final, polylines, corresponding_pairs, following_polylines, heading_polylines, cells, cell_edges_labeled, all_slicing_lines, lawnmower_lines
    
    # Collect all line segments from all cells into a global list
    # Each line has: line_idx (global), cell_idx, endpoints, visited flag
    all_lines = []
    global_line_idx = 0
    
    for cell_data in all_slicing_lines:
        cell_idx = cell_data['cell_idx']
        for line in cell_data['lines']:
            p1, p2 = line
            all_lines.append({
                'global_idx': global_line_idx,
                'cell_idx': cell_idx,
                'p1': p1,
                'p2': p2,
                'visited': False
            })
            global_line_idx += 1
    
    print(f"Collected {len(all_lines)} line segments from {len(all_slicing_lines)} cells")
    
    # Print all line endpoints for debugging
    print(f"\nAll line segments:")
    for i, line in enumerate(all_lines):
        print(f"  Line {i} (Cell {line['cell_idx']}): ({line['p1'][0]:.2f}, {line['p1'][1]:.2f}) → ({line['p2'][0]:.2f}, {line['p2'][1]:.2f})")
    
    # Connection threshold: 1 cm = 0.01 m
    CONNECTION_THRESHOLD = 0.01
    
    print(f"\nConnection threshold: {CONNECTION_THRESHOLD * 100:.2f} cm ({CONNECTION_THRESHOLD} m)")
    
    # Build lawnmower lines by grouping connected slicing lines
    visited = [False] * len(all_lines)
    
    for start_idx in range(len(all_lines)):
        if visited[start_idx]:
            continue
        
        # Start a new lawnmower line
        current_lawnmower = []
        current_line_idx = start_idx
        visited[current_line_idx] = True
        
        # Add the first line to the lawnmower
        current_line = all_lines[current_line_idx]
        
        # IMPORTANT: Determine which direction has more connections
        # Check both p1 and p2 to see which endpoint has unvisited connections
        connections_from_p1 = 0
        connections_from_p2 = 0
        
        for idx, line in enumerate(all_lines):
            if visited[idx]:
                continue
            
            # Check distances from p1
            dist_p1_to_p1 = math.sqrt((current_line['p1'][0] - line['p1'][0])**2 + 
                                     (current_line['p1'][1] - line['p1'][1])**2)
            dist_p1_to_p2 = math.sqrt((current_line['p1'][0] - line['p2'][0])**2 + 
                                     (current_line['p1'][1] - line['p2'][1])**2)
            
            if dist_p1_to_p1 <= CONNECTION_THRESHOLD or dist_p1_to_p2 <= CONNECTION_THRESHOLD:
                connections_from_p1 += 1
            
            # Check distances from p2
            dist_p2_to_p1 = math.sqrt((current_line['p2'][0] - line['p1'][0])**2 + 
                                     (current_line['p2'][1] - line['p1'][1])**2)
            dist_p2_to_p2 = math.sqrt((current_line['p2'][0] - line['p2'][0])**2 + 
                                     (current_line['p2'][1] - line['p2'][1])**2)
            
            if dist_p2_to_p1 <= CONNECTION_THRESHOLD or dist_p2_to_p2 <= CONNECTION_THRESHOLD:
                connections_from_p2 += 1
        
        # Start from the endpoint with MORE connections (or p1 if no connections)
        # If connections from p1 > connections from p2, REVERSE the line so we traverse p2->p1
        if connections_from_p1 > connections_from_p2:
            # Reverse the first line so we start from p2 and traverse toward p1
            current_lawnmower.append({
                'global_idx': current_line['global_idx'],
                'cell_idx': current_line['cell_idx'],
                'p1': current_line['p2'],  # Reversed
                'p2': current_line['p1'],  # Reversed
                'visited': True
            })
            current_endpoint = current_line['p1']  # Will search from p1 (now the "end")
            print(f"\n  Starting lawnmower line {len(lawnmower_lines) + 1} from line {start_idx} (Cell {current_line['cell_idx']}) REVERSED")
            print(f"    Initial line: ({current_line['p2'][0]:.2f}, {current_line['p2'][1]:.2f}) → ({current_line['p1'][0]:.2f}, {current_line['p1'][1]:.2f}) [REVERSED]")
            print(f"    Reason: {connections_from_p1} connection(s) from p1 vs {connections_from_p2} from p2")
        else:
            # Keep original direction
            current_lawnmower.append(current_line)
            current_endpoint = current_line['p2']
            print(f"\n  Starting lawnmower line {len(lawnmower_lines) + 1} from line {start_idx} (Cell {current_line['cell_idx']})")
            print(f"    Initial line: ({current_line['p1'][0]:.2f}, {current_line['p1'][1]:.2f}) → ({current_line['p2'][0]:.2f}, {current_line['p2'][1]:.2f})")
            print(f"    Reason: {connections_from_p2} connection(s) from p2 vs {connections_from_p1} from p1")
        
        print(f"    Searching from endpoint: ({current_endpoint[0]:.2f}, {current_endpoint[1]:.2f})")
        
        # Keep extending the lawnmower line
        while True:
            # Find the closest unvisited line whose endpoint is within threshold
            min_dist = float('inf')
            next_line_idx = None
            next_line_reversed = False
            
            for idx, line in enumerate(all_lines):
                if visited[idx]:
                    continue
                
                # Check distance from current_endpoint to both endpoints of this line
                dist_to_p1 = math.sqrt((current_endpoint[0] - line['p1'][0])**2 + 
                                      (current_endpoint[1] - line['p1'][1])**2)
                dist_to_p2 = math.sqrt((current_endpoint[0] - line['p2'][0])**2 + 
                                      (current_endpoint[1] - line['p2'][1])**2)
                
                # Use the closer endpoint
                if dist_to_p1 < dist_to_p2:
                    if dist_to_p1 < min_dist and dist_to_p1 <= CONNECTION_THRESHOLD:
                        min_dist = dist_to_p1
                        next_line_idx = idx
                        next_line_reversed = False  # Connect via p1, so traverse p1->p2
                else:
                    if dist_to_p2 < min_dist and dist_to_p2 <= CONNECTION_THRESHOLD:
                        min_dist = dist_to_p2
                        next_line_idx = idx
                        next_line_reversed = True  # Connect via p2, so traverse p2->p1
            
            # If no connected line found, end this lawnmower
            if next_line_idx is None:
                print(f"    No more connected lines found within {CONNECTION_THRESHOLD*100:.2f} cm threshold")
                break
            
            # Add the next line to the lawnmower
            next_line = all_lines[next_line_idx]
            visited[next_line_idx] = True
            
            print(f"    ✓ Connected to line {next_line_idx} (Cell {next_line['cell_idx']}), distance={min_dist*100:.4f} cm, reversed={next_line_reversed}")
            
            # Store the line with orientation info
            if next_line_reversed:
                # Traverse from p2 to p1
                current_lawnmower.append({
                    'global_idx': next_line['global_idx'],
                    'cell_idx': next_line['cell_idx'],
                    'p1': next_line['p2'],  # Reversed
                    'p2': next_line['p1'],  # Reversed
                    'visited': True
                })
                current_endpoint = next_line['p1']
            else:
                # Traverse from p1 to p2
                current_lawnmower.append(next_line)
                current_endpoint = next_line['p2']
        
        # Add this lawnmower line to the list
        lawnmower_lines.append(current_lawnmower)
        print(f"  Completed lawnmower line {len(lawnmower_lines)}: {len(current_lawnmower)} segments")
    
    print(f"\n✓ Generated {len(lawnmower_lines)} lawnmower lines")
    
    # Display statistics for each lawnmower line
    print(f"\nLawnmower line statistics:")
    for i, lawnmower in enumerate(lawnmower_lines):
        # Calculate total length
        total_length = 0
        for line in lawnmower:
            dx = line['p2'][0] - line['p1'][0]
            dy = line['p2'][1] - line['p1'][1]
            length = math.sqrt(dx**2 + dy**2)
            total_length += length
        
        # Get start and end points
        start_point = lawnmower[0]['p1']
        end_point = lawnmower[-1]['p2']
        
        print(f"  Line {i+1}:")
        print(f"    Segments: {len(lawnmower)}")
        print(f"    Total length: {total_length:.2f} m")
        print(f"    Start: ({start_point[0]:.2f}, {start_point[1]:.2f})")
        print(f"    End: ({end_point[0]:.2f}, {end_point[1]:.2f})")
    
    print(f"\n{'='*60}")
    print(f"LAWNMOWER LINE GENERATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total lawnmower lines: {len(lawnmower_lines)}")
    print(f"{'='*60}\n")

    # ========================================================================
    # WAYPOINT GENERATION FROM LAWNMOWER LINES
    # ========================================================================
    print(f"\n{'='*60}")
    print("GENERATING WAYPOINTS FROM LAWNMOWER LINES")
    print(f"{'='*60}\n")
    
    waypoints_final = []

    start_opposite_end = True  # Whether to start from the opposite end of the closest lawnmower line
    
    if len(lawnmower_lines) == 0:
        print("No lawnmower lines to convert to waypoints")
        return waypoints_final, polylines, corresponding_pairs, following_polylines, heading_polylines, cells, cell_edges_labeled, all_slicing_lines, lawnmower_lines
    
    # STEP 1: Find the lawnmower line closest to the longest polyline
    # The longest polyline is at index 0 (already sorted)
    longest_polyline_indices = polylines[0]
    
    # Get the coordinates of the longest polyline
    longest_polyline_coords = [polygon_m[idx] for idx in longest_polyline_indices]
    
    # Get the two endpoints of the longest polyline
    longest_p1 = longest_polyline_coords[0]   # First endpoint
    longest_p2 = longest_polyline_coords[-1]  # Last endpoint
    
    print(f"Longest polyline endpoints:")
    print(f"  p1: ({longest_p1[0]:.2f}, {longest_p1[1]:.2f})")
    print(f"  p2: ({longest_p2[0]:.2f}, {longest_p2[1]:.2f})")
    
    # Find the lawnmower line with the closest endpoint to either endpoint of the longest polyline
    min_dist_to_longest = float('inf')
    starting_line_idx = 0
    start_from_p1 = True  # Variable to choose which end to start from
    
    for i, lawnmower in enumerate(lawnmower_lines):
        # Get the two endpoints of this lawnmower line
        p1 = lawnmower[0]['p1']  # Start of first segment
        p2 = lawnmower[-1]['p2']  # End of last segment
        
        # Calculate all four possible distances using helper function
        # 1. lawnmower p1 to longest polyline p1
        dist_p1_to_longest_p1 = euclidean_distance(p1, longest_p1)
        # 2. lawnmower p1 to longest polyline p2
        dist_p1_to_longest_p2 = euclidean_distance(p1, longest_p2)
        # 3. lawnmower p2 to longest polyline p1
        dist_p2_to_longest_p1 = euclidean_distance(p2, longest_p1)
        # 4. lawnmower p2 to longest polyline p2
        dist_p2_to_longest_p2 = euclidean_distance(p2, longest_p2)
        
        # Find the minimum distance among all four combinations
        min_dist_p1 = min(dist_p1_to_longest_p1, dist_p1_to_longest_p2)
        min_dist_p2 = min(dist_p2_to_longest_p1, dist_p2_to_longest_p2)
        
        # Check if either endpoint is closer than current minimum
        if min_dist_p1 < min_dist_to_longest:
            min_dist_to_longest = min_dist_p1
            starting_line_idx = i
            start_from_p1 = True
        
        if min_dist_p2 < min_dist_to_longest:
            min_dist_to_longest = min_dist_p2
            starting_line_idx = i
            start_from_p1 = False
    
    # Apply start_opposite_end variable to flip the starting direction if desired
    if start_opposite_end:
        start_from_p1 = not start_from_p1
        print(f"\n⚠ start_opposite_end is True - flipping to opposite endpoint")
    
    print(f"\nStarting lawnmower line: Line {starting_line_idx + 1}")
    print(f"  Distance to longest polyline: {min_dist_to_longest:.2f} m")
    print(f"  Start from {'p1 (first endpoint)' if start_from_p1 else 'p2 (last endpoint)'}")
    print(f"  start_opposite_end = {start_opposite_end}")
    
    # STEP 2: Build the waypoint path using nearest-neighbor algorithm
    # Track which lawnmower lines have been visited
    visited_lines = [False] * len(lawnmower_lines)
    
    # Start with the selected lawnmower line
    current_line_idx = starting_line_idx
    visited_lines[current_line_idx] = True
    
    # Add waypoints from the starting line
    current_lawnmower = lawnmower_lines[current_line_idx]
    
    if start_from_p1:
        # Traverse from p1 to p2 (normal order)
        for segment in current_lawnmower:
            if len(waypoints_final) == 0:
                # First waypoint: add p1
                waypoints_final.append((segment['p1'][0], segment['p1'][1], altitude))
            # Always add p2 (end of segment)
            waypoints_final.append((segment['p2'][0], segment['p2'][1], altitude))
        current_endpoint = current_lawnmower[-1]['p2']
    else:
        # Traverse from p2 to p1 (reverse order)
        for segment in reversed(current_lawnmower):
            if len(waypoints_final) == 0:
                # First waypoint: add p2 (reversed)
                waypoints_final.append((segment['p2'][0], segment['p2'][1], altitude))
            # Always add p1 (reversed)
            waypoints_final.append((segment['p1'][0], segment['p1'][1], altitude))
        current_endpoint = current_lawnmower[0]['p1']
    
    print(f"\n  Added {len(waypoints_final)} waypoints from starting line")
    print(f"  Current endpoint: ({current_endpoint[0]:.2f}, {current_endpoint[1]:.2f})")
    
    # STEP 3: Iteratively find and add the closest unvisited lawnmower line
    for iteration in range(len(lawnmower_lines) - 1):
        # Find the closest unvisited lawnmower line
        min_dist = float('inf')
        next_line_idx = None
        next_start_from_p1 = True
        
        for i, lawnmower in enumerate(lawnmower_lines):
            if visited_lines[i]:
                continue
            
            # Get the two endpoints of this lawnmower line
            p1 = lawnmower[0]['p1']
            p2 = lawnmower[-1]['p2']
            
            # Distance from current endpoint to p1
            dist_to_p1 = math.sqrt((current_endpoint[0] - p1[0])**2 + 
                                   (current_endpoint[1] - p1[1])**2)
            
            # Distance from current endpoint to p2
            dist_to_p2 = math.sqrt((current_endpoint[0] - p2[0])**2 + 
                                   (current_endpoint[1] - p2[1])**2)
            
            # Choose the closer endpoint
            if dist_to_p1 < dist_to_p2:
                if dist_to_p1 < min_dist:
                    min_dist = dist_to_p1
                    next_line_idx = i
                    next_start_from_p1 = True
            else:
                if dist_to_p2 < min_dist:
                    min_dist = dist_to_p2
                    next_line_idx = i
                    next_start_from_p1 = False
        
        if next_line_idx is None:
            print(f"\n  Warning: No more unvisited lines found at iteration {iteration + 1}")
            break
        
        # Add transition waypoint (link between lawnmower lines)
        next_lawnmower = lawnmower_lines[next_line_idx]
        
        if next_start_from_p1:
            transition_point = next_lawnmower[0]['p1']
        else:
            transition_point = next_lawnmower[-1]['p2']
        
        # Add the transition waypoint
        waypoints_final.append((transition_point[0], transition_point[1], altitude))
        
        print(f"\n  Transition to Line {next_line_idx + 1}:")
        print(f"    Distance: {min_dist:.2f} m")
        print(f"    Start from {'p1 (first endpoint)' if next_start_from_p1 else 'p2 (last endpoint)'}")
        
        # Mark as visited
        visited_lines[next_line_idx] = True
        
        # Add waypoints from the next lawnmower line
        waypoints_before = len(waypoints_final)
        
        if next_start_from_p1:
            # Traverse from p1 to p2 (normal order)
            for segment in next_lawnmower:
                # Skip p1 (already added as transition point)
                waypoints_final.append((segment['p2'][0], segment['p2'][1], altitude))
            current_endpoint = next_lawnmower[-1]['p2']
        else:
            # Traverse from p2 to p1 (reverse order)
            for segment in reversed(next_lawnmower):
                # Skip p2 (already added as transition point)
                waypoints_final.append((segment['p1'][0], segment['p1'][1], altitude))
            current_endpoint = next_lawnmower[0]['p1']
        
        waypoints_added = len(waypoints_final) - waypoints_before
        print(f"    Added {waypoints_added} waypoints from this line")
        print(f"    Total waypoints: {len(waypoints_final)}")
        print(f"    Current endpoint: ({current_endpoint[0]:.2f}, {current_endpoint[1]:.2f})")
    
    print(f"\n{'='*60}")
    print(f"WAYPOINT GENERATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total waypoints generated: {len(waypoints_final)}")
    print(f"Lawnmower lines visited: {sum(visited_lines)}/{len(lawnmower_lines)}")
    print(f"{'='*60}\n")
    
    return waypoints_final, polylines, corresponding_pairs, following_polylines, heading_polylines, cells, cell_edges_labeled, all_slicing_lines, lawnmower_lines

# ============================================================================
# SECTION 6: MISSION STATISTICS & ANALYSIS
# Calculates flight time, distance, and mission metrics
# ============================================================================
def calculate_mission_stats(waypoints, speed, forward_overlap, altitude, vfov):
    """Calculate mission statistics."""
    if len(waypoints) < 2:
        return {}
    
    # Calculate total distance
    total_distance = 0
    for i in range(len(waypoints) - 1):
        x1, y1, _ = waypoints[i]
        x2, y2, _ = waypoints[i + 1]
        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        total_distance += distance
    
    # Calculate flight time
    flight_time = total_distance / speed  # seconds
    
    # Calculate number of photos
    photo_distance = calculate_photo_distance(altitude, vfov, forward_overlap)
    num_photos = int(total_distance / photo_distance) if photo_distance > 0 else 0
    
    # Calculate polygon area (approximate)
    # Using shoelace formula on first/last polygon
    
    return {
        'total_distance': total_distance,
        'flight_time': flight_time,
        'num_photos': num_photos,
        'num_waypoints': len(waypoints)
    }


# ============================================================================
# SECTION 7: VISUALIZATION & DISPLAY HELPERS
# Functions for rendering and displaying mission data
# ============================================================================
# ============================================================================
# SECTION 8: INTERACTIVE UI EVENT HANDLERS
# Matplotlib event callbacks for polygon drawing and interaction
# ============================================================================
def on_click(event):
    """Handle mouse click events for polygon drawing."""
    global polygon_points, polygon_patch, line, polygon_closed, waypoints
    
    if event.inaxes != ax:
        return
    
    # Regular polygon drawing (left click)
    if event.button == 1 and not polygon_closed:  # Left click
        polygon_points.append((event.xdata, event.ydata))
        
        # Update display
        if len(polygon_points) == 1:
            # First point
            line, = ax.plot([event.xdata], [event.ydata], 'ro-', linewidth=2, markersize=6)
        else:
            # Update line
            xs, ys = zip(*polygon_points)
            line.set_data(xs, ys)
        
        plt.draw()
        print(f"Point {len(polygon_points)}: ({event.xdata:.2f}, {event.ydata:.2f})")
    
    # Right click - close polygon
    elif event.button == 3 and not polygon_closed and len(polygon_points) >= 3:
        close_polygon()


def on_key(event):
    """Handle keyboard events."""
    global polygon_closed
    
    if event.key == 'enter' and not polygon_closed and len(polygon_points) >= 3:
        close_polygon()


def close_polygon():
    """Close the polygon and generate mission automatically."""
    global polygon_closed, polygon_patch, line
    
    polygon_closed = True
    print(f"\n✓ Polygon closed with {len(polygon_points)} vertices")
    
    # Draw filled polygon
    if polygon_patch:
        polygon_patch.remove()
    
    polygon_patch = MplPolygon(polygon_points, alpha=0.3, facecolor='lightblue', 
                              edgecolor='blue', linewidth=2)
    ax.add_patch(polygon_patch)
    
    # Remove the line
    if line:
        line.remove()
    
    # Draw vertices
    xs, ys = zip(*polygon_points)
    ax.plot(xs, ys, 'bo', markersize=8)
    
    plt.draw()
    
    # Automatically generate the flight path
    print(f"\nUsing reference coordinates: {reference_lat:.6f}, {reference_lon:.6f}")
    generate_and_display_mission()


def generate_and_display_mission():
    """Generate flight path and display it."""
    global waypoints
    
    # Convert polygon points to meters using NumPy for efficiency
    # Use first polygon point as local origin (0, 0)
    origin_x, origin_y = polygon_points[0]
    scale = 1.0  # 1:1 mapping for now
    
    # Vectorized conversion to meters
    polygon_array = np.array(polygon_points)
    origin = np.array([origin_x, origin_y])
    polygon_m_array = (polygon_array - origin) * scale
    polygon_m = [tuple(p) for p in polygon_m_array]
    
    print(f"\nPolygon in meters (relative to first point):")
    for i, (x, y) in enumerate(polygon_m):
        print(f"  Point {i+1}: ({x:.2f}, {y:.2f})")
    
    # Generate survey grid with polyline decomposition
    waypoints, polylines, corresponding_pairs, following_polylines, heading_polylines, cells, cell_edges_labeled, all_slicing_lines, lawnmower_lines = generate_survey_grid(
        polygon_m,
        MISSION_PARAMS['altitude'],
        MISSION_PARAMS['camera_hfov'],
        MISSION_PARAMS['camera_vfov'],
        MISSION_PARAMS['lateral_overlap'],
        MISSION_PARAMS['grid_angle']
    )
    
    # Visualize polylines with different colors
    colors = ['red', 'green', 'blue', 'orange', 'purple', 'cyan', 'magenta', 'yellow']
    
    print(f"\nVisualizing {len(polylines)} polylines with different colors:")
    for i, polyline_indices in enumerate(polylines):
        color = colors[i % len(colors)]
        
        # Convert polyline vertices to canvas coordinates
        polyline_canvas_points = []
        for idx in polyline_indices:
            px = (polygon_m[idx][0] / scale) + origin_x
            py = (polygon_m[idx][1] / scale) + origin_y
            polyline_canvas_points.append((px, py))
        
        # Draw polyline with thick colored line
        if len(polyline_canvas_points) >= 2:
            xs, ys = zip(*polyline_canvas_points)
            ax.plot(xs, ys, color=color, linewidth=4, alpha=0.8, 
                   label=f'Polyline {i+1} ({len(polyline_indices)} vertices)')
            
            # Mark vertices
            ax.plot(xs, ys, 'o', color=color, markersize=10, alpha=0.6)
        
        print(f"  Polyline {i+1}: {color} - vertices {polyline_indices}")
    
    # Visualize corresponding pairs as dashed lines (without labels)
    if len(corresponding_pairs) > 0:
        print(f"\nVisualizing {len(corresponding_pairs)} corresponding pairs as dashed lines")
        
        for pair in corresponding_pairs:
            # Convert points from meters to canvas coordinates
            x1_m, y1_m = pair['point_1']
            x2_m, y2_m = pair['point_2']
            
            px1 = (x1_m / scale) + origin_x
            py1 = (y1_m / scale) + origin_y
            px2 = (x2_m / scale) + origin_x
            py2 = (y2_m / scale) + origin_y
            
            # Draw dashed line connecting the pair
            ax.plot([px1, px2], [py1, py2], 'gray', linewidth=2, 
                   linestyle='--', alpha=0.5)
        
        print(f"  ✓ Drew {len(corresponding_pairs)} dashed lines (gray)")
    
    # Add legend and redraw main canvas
    ax.legend(loc='upper right', fontsize=8)
    plt.draw()
    
    # Create second canvas for cell visualization
    if len(cells) > 0:
        print(f"\n{'='*60}")
        print("CREATING CELL VISUALIZATION CANVAS")
        print(f"{'='*60}\n")
        
        # Create second figure for cell visualization
        global fig_cells, ax_cells
        fig_cells, ax_cells = plt.subplots(figsize=(12, 10))
        ax_cells.set_xlim(0, 500)
        ax_cells.set_ylim(0, 500)
        ax_cells.set_aspect('equal')
        ax_cells.grid(True, alpha=0.3)
        ax_cells.set_title('Cell Decomposition Visualization', fontsize=14, fontweight='bold')
        ax_cells.set_xlabel('X (canvas units)', fontsize=10)
        ax_cells.set_ylabel('Y (canvas units)', fontsize=10)
        
        # Draw original polygon as background
        ax_cells.add_patch(MplPolygon(polygon_points, alpha=0.1, facecolor='lightgray', 
                                    edgecolor='gray', linewidth=1))
        
        # Draw following polylines as black lines
        print(f"Drawing following polylines on cell canvas:")
        for i in following_polylines:
            polyline_indices = polylines[i]
            polyline_canvas_points = []
            for idx in polyline_indices:
                px = (polygon_m[idx][0] / scale) + origin_x
                py = (polygon_m[idx][1] / scale) + origin_y
                polyline_canvas_points.append((px, py))
            
            if len(polyline_canvas_points) >= 2:
                xs, ys = zip(*polyline_canvas_points)
                ax_cells.plot(xs, ys, 'k-', linewidth=3, alpha=0.8)
        
        print(f"  ✓ Drew {len(following_polylines)} following polylines")
        
        # Draw cell polygons with different colors
        cell_colors = ['lightcoral', 'lightgreen', 'lightblue', 'lightyellow', 
                      'lightcyan', 'lightpink', 'lightgray', 'wheat']
        
        print(f"\nDrawing {len(cells)} cell polygons:")
        for cell_idx, cell_vertices in enumerate(cells):
            if len(cell_vertices) < 3:
                continue
                
            # Convert to canvas coordinates using helper function
            cell_canvas_points = convert_to_canvas_coords(cell_vertices, scale, origin_x, origin_y)
            
            # Draw filled cell polygon
            color = cell_colors[cell_idx % len(cell_colors)]
            cell_patch = MplPolygon(cell_canvas_points, alpha=0.4, facecolor=color, 
                                  edgecolor='black', linewidth=2)
            ax_cells.add_patch(cell_patch)
            
            # Calculate cell centroid using shoelace formula for proper geometric center
            n = len(cell_canvas_points)
            area = 0.0
            center_x = 0.0
            center_y = 0.0
            
            for i in range(n):
                x1, y1 = cell_canvas_points[i]
                x2, y2 = cell_canvas_points[(i + 1) % n]
                cross = x1 * y2 - x2 * y1
                area += cross
                center_x += (x1 + x2) * cross
                center_y += (y1 + y2) * cross
            
            area /= 2.0
            if abs(area) > 1e-10:
                center_x /= (6.0 * area)
                center_y /= (6.0 * area)
            else:
                # Fallback to simple average if area is too small
                xs, ys = zip(*cell_canvas_points)
                center_x = sum(xs) / len(xs)
                center_y = sum(ys) / len(ys)
            
            # Add cell label
            ax_cells.text(center_x, center_y, f'Cell {cell_idx}', 
                         ha='center', va='center', fontsize=12, fontweight='bold',
                         bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
            
            
            # Draw edge labels
            # Label types: 1=heading (red), 2=direction (green), 3=corresponding (blue), 4=other (gray)
            if cell_idx < len(cell_edges_labeled):
                labeled_edges = cell_edges_labeled[cell_idx]
                label_colors = {1: 'red', 2: 'green', 3: 'blue', 4: 'gray'}
                
                for edge_info in labeled_edges:
                    # Get edge vertices in meters
                    v1_m = edge_info['v1']
                    v2_m = edge_info['v2']
                    
                    # Convert to canvas coordinates
                    x1 = (v1_m[0] / scale) + origin_x
                    y1 = (v1_m[1] / scale) + origin_y
                    x2 = (v2_m[0] / scale) + origin_x
                    y2 = (v2_m[1] / scale) + origin_y
                    
                    # Calculate edge midpoint
                    mid_x = (x1 + x2) / 2
                    mid_y = (y1 + y2) / 2
                    
                    # Draw label circle
                    label = edge_info['label']
                    color = label_colors[label]
                    
                    # Draw circle with label number
                    circle = plt.Circle((mid_x, mid_y), radius=5, 
                                      facecolor=color, edgecolor='black', 
                                      linewidth=1.5, alpha=0.8, zorder=10)
                    ax_cells.add_patch(circle)
                    
                    # Add label number in white
                    ax_cells.text(mid_x, mid_y, str(label), 
                                ha='center', va='center', fontsize=8, 
                                color='white', fontweight='bold', zorder=11)
            
            print(f"  Cell {cell_idx}: {color}, {len(cell_vertices)} vertices")
        
        # Add legend for edge labels
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='red', edgecolor='black', label='1: Heading Edge'),
            Patch(facecolor='green', edgecolor='black', label='2: Direction Edge'),
            Patch(facecolor='blue', edgecolor='black', label='3: Corresponding Edge'),
            Patch(facecolor='gray', edgecolor='black', label='4: Other Edge')
        ]
        ax_cells.legend(handles=legend_elements, loc='upper right', fontsize=9,
                       title='Edge Labels', framealpha=0.9)
        
        print(f"\n✓ Created cell visualization canvas with {len(cells)} cells")
        print(f"{'='*60}\n")
        
        # Show the cell canvas
        plt.figure(fig_cells)
        plt.tight_layout()
        plt.show(block=False)
    
    # Create third canvas for lawnmower line visualization
    if len(lawnmower_lines) > 0:
        print(f"\n{'='*60}")
        print("CREATING LAWNMOWER LINE VISUALIZATION CANVAS")
        print(f"{'='*60}\n")
        
        # Create third figure for lawnmower lines
        global fig_lawnmower, ax_lawnmower
        fig_lawnmower, ax_lawnmower = plt.subplots(figsize=(12, 10))
        ax_lawnmower.set_xlim(0, 500)
        ax_lawnmower.set_ylim(0, 500)
        ax_lawnmower.set_aspect('equal')
        ax_lawnmower.grid(True, alpha=0.3)
        ax_lawnmower.set_title('Lawnmower Lines Visualization', fontsize=14, fontweight='bold')
        ax_lawnmower.set_xlabel('X (canvas units)', fontsize=10)
        ax_lawnmower.set_ylabel('Y (canvas units)', fontsize=10)
        
        # Draw original polygon as background
        ax_lawnmower.add_patch(MplPolygon(polygon_points, alpha=0.1, facecolor='lightgray', 
                                    edgecolor='gray', linewidth=1))
        
        # Draw cells as faint outlines for reference
        cell_colors = ['lightcoral', 'lightgreen', 'lightblue', 'lightyellow', 
                      'lightcyan', 'lightpink', 'lightgray', 'wheat']
        
        for cell_idx, cell_vertices in enumerate(cells):
            if len(cell_vertices) < 3:
                continue
                
            # Convert to canvas coordinates using helper function
            cell_canvas_points = convert_to_canvas_coords(cell_vertices, scale, origin_x, origin_y)
            
            # Draw cell outline only (no fill)
            color = cell_colors[cell_idx % len(cell_colors)]
            cell_patch = MplPolygon(cell_canvas_points, alpha=0.2, facecolor='none', 
                                  edgecolor=color, linewidth=1, linestyle='--')
            ax_lawnmower.add_patch(cell_patch)
        
        # Draw lawnmower lines with different colors
        lawnmower_colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'olive']
        
        print(f"Drawing {len(lawnmower_lines)} lawnmower lines:")
        for lm_idx, lawnmower in enumerate(lawnmower_lines):
            color = lawnmower_colors[lm_idx % len(lawnmower_colors)]
            
            # Collect all points in order for this lawnmower line
            lawnmower_path = []
            for segment in lawnmower:
                if len(lawnmower_path) == 0:
                    # First segment, add both points
                    lawnmower_path.append(segment['p1'])
                # Always add the end point
                lawnmower_path.append(segment['p2'])
            
            # Convert to canvas coordinates
            lawnmower_canvas = []
            for x_m, y_m in lawnmower_path:
                px = (x_m / scale) + origin_x
                py = (y_m / scale) + origin_y
                lawnmower_canvas.append((px, py))
            
            # Draw the lawnmower line
            if len(lawnmower_canvas) >= 2:
                xs, ys = zip(*lawnmower_canvas)
                ax_lawnmower.plot(xs, ys, '-', color=color, linewidth=2.5, 
                                alpha=0.8, label=f'Line {lm_idx+1} ({len(lawnmower)} seg)')
                
                # Mark start with circle
                ax_lawnmower.plot(xs[0], ys[0], 'o', color=color, markersize=10, 
                                markeredgecolor='black', markeredgewidth=1.5)
                
                # Mark end with square
                ax_lawnmower.plot(xs[-1], ys[-1], 's', color=color, markersize=10,
                                markeredgecolor='black', markeredgewidth=1.5)
                
                # Add direction arrows at midpoints of segments
                for i in range(len(xs) - 1):
                    mid_x = (xs[i] + xs[i+1]) / 2
                    mid_y = (ys[i] + ys[i+1]) / 2
                    dx = xs[i+1] - xs[i]
                    dy = ys[i+1] - ys[i]
                    length = math.sqrt(dx**2 + dy**2)
                    if length > 1e-6:
                        # Normalize and scale for arrow
                        arrow_scale = min(10, length * 0.2)
                        dx = dx / length * arrow_scale
                        dy = dy / length * arrow_scale
                        ax_lawnmower.arrow(mid_x - dx/2, mid_y - dy/2, dx, dy,
                                         head_width=3, head_length=2, fc=color, ec=color,
                                         linewidth=1.5, alpha=0.7, length_includes_head=True)
                
                print(f"  Line {lm_idx+1}: {color}, {len(lawnmower)} segments, {len(lawnmower_path)} points")
        
        # Add legend
        ax_lawnmower.legend(loc='upper right', fontsize=9, framealpha=0.9,
                          title='Lawnmower Lines\n(○=start, □=end)')
        
        print(f"\n✓ Created lawnmower line visualization canvas with {len(lawnmower_lines)} lines")
        print(f"{'='*60}\n")
        
        # Show the lawnmower canvas
        plt.figure(fig_lawnmower)
        plt.tight_layout()
        plt.show(block=False)
    
    # Calculate and display statistics
    # Convert waypoints back to canvas coordinates for display using helper function
    waypoints_m = [(x_m, y_m) for x_m, y_m, alt in waypoints]
    waypoints_canvas = convert_to_canvas_coords(waypoints_m, scale, origin_x, origin_y)
    
    # Plot flight path
    if len(waypoints_canvas) > 0:
        # Draw path lines
        xs, ys = zip(*waypoints_canvas)
        ax.plot(xs, ys, 'k-', linewidth=1.5, alpha=0.5, label='Flight Path')
        ax.plot(xs, ys, 'ko', markersize=3, alpha=0.5)
        
        # Number waypoints
        for i, (x, y) in enumerate(waypoints_canvas):
            if i % 4 == 0:  # Label every 4th waypoint to avoid clutter
                ax.annotate(str(i+1), (x, y), fontsize=7, ha='right', alpha=0.7)
        
        ax.legend(loc='upper right', fontsize=8)
        plt.draw()
    
    # Calculate and display statistics
    stats = calculate_mission_stats(
        waypoints,
        MISSION_PARAMS['aircraft_speed'],
        MISSION_PARAMS['forward_overlap'],
        MISSION_PARAMS['altitude'],
        MISSION_PARAMS['camera_vfov']
    )
    
    if len(waypoints) > 0:
        print("\n" + "="*60)
        print("MISSION STATISTICS")
        print("="*60)
        print(f"Total Distance: {stats.get('total_distance', 0):.1f} m ({stats.get('total_distance', 0)/1000:.2f} km)")
        print(f"Flight Time: {stats.get('flight_time', 0)/60:.1f} minutes")
        print(f"Estimated Photos: {stats.get('num_photos', 0)}")
        print(f"Number of Waypoints: {stats.get('num_waypoints', 0)}")
        
        # Calculate GSD
        gsd = calculate_gsd(MISSION_PARAMS['altitude'], MISSION_PARAMS['camera_hfov'], 
                           MISSION_PARAMS['camera_width'])
        print(f"Ground Sampling Distance: {gsd:.2f} cm/pixel")
        print("="*60 + "\n")
    else:
        print("\n⚠ No waypoints generated yet (waypoints_final is empty)")
    
    print("\n✓ Mission generation complete!")
    print("Close the window to exit.")


# ============================================================================
# SECTION 9: MAIN APPLICATION ENTRY POINT
# Initializes the application and runs interactive polygon drawing mode
# ============================================================================
def main():
    """Main program entry point."""
    global fig, ax
    
    # Check for test mode
    test_mode = len(sys.argv) > 1 and sys.argv[1] == '--test'
    
    # Set matplotlib backend based on mode
    if test_mode:
        matplotlib.use('Agg')  # Non-interactive for headless testing
    else:
        # Try to use an interactive backend for GUI mode
        try:
            matplotlib.use('TkAgg')  # Try TkAgg first
        except:
            try:
                matplotlib.use('Qt5Agg')  # Fallback to Qt5Agg
            except:
                matplotlib.use('Agg')  # Final fallback to non-interactive
    
    print("\n" + "="*60)
    print("MISSION PLANNER DEVELOPMENT TOOL")
    print("Survey Grid Generator")
    print("="*60)
    print("\nMISSION PARAMETERS:")
    for key, value in MISSION_PARAMS.items():
        print(f"  {key}: {value}")
    print("\n" + "="*60)
    
    if test_mode:
        print("TEST MODE: Using predefined polygon")
        print("="*60 + "\n")
        
        # Use a predefined test polygon
        test_polygon = [(100, 100), (400, 100), (400, 300), (300, 400), (200, 350), (100, 300), (100, 100)]
        
        # Simulate polygon creation
        global polygon_points, polygon_closed
        polygon_points = test_polygon
        polygon_closed = True
        
        # Create figure for display
        fig, ax = plt.subplots(figsize=(12, 10))
        ax.set_xlim(0, 500)
        ax.set_ylim(0, 500)
        ax.set_aspect('equal')
        ax.set_title('Survey Mission Planner - Test Mode', fontsize=14, fontweight='bold')
        ax.set_xlabel('X (canvas units)', fontsize=10)
        ax.set_ylabel('Y (canvas units)', fontsize=10)
        
        # Draw the test polygon
        polygon_patch = MplPolygon(polygon_points, alpha=0.3, facecolor='lightblue', 
                                  edgecolor='blue', linewidth=2)
        ax.add_patch(polygon_patch)
        
        # Draw vertices
        xs, ys = zip(*polygon_points)
        ax.plot(xs, ys, 'bo', markersize=8)
        
        plt.draw()
        
        # Generate mission automatically
        generate_and_display_mission()
        
        # Save plots to files instead of showing
        plt.savefig('main_canvas_test.png', dpi=150, bbox_inches='tight')
        print("✓ Main canvas saved to: main_canvas_test.png")
        
        # Save cell canvas if it exists
        if fig_cells is not None:
            plt.figure(fig_cells)
            plt.savefig('cell_canvas_test.png', dpi=150, bbox_inches='tight')
            print("✓ Cell canvas saved to: cell_canvas_test.png")
        else:
            print("⚠ Cell canvas not created (no corresponding pairs)")
        
        print("\n" + "="*60)
        print("Test completed successfully!")
        print("Check main_canvas_test.png and cell_canvas_test.png")
        print("="*60)
        
    else:
        print("INSTRUCTIONS:")
        print("  1. LEFT-CLICK to add polygon vertices")
        print("  2. Press ENTER or RIGHT-CLICK to close polygon")
        print("  3. Flight path will be generated automatically")
        print(f"\nReference Origin: {reference_lat:.6f}, {reference_lon:.6f}")
        print("  (Edit reference_lat/reference_lon in script to change)")
        print("="*60 + "\n")
        
        # Create interactive plot
        fig, ax = plt.subplots(figsize=(12, 10))
        ax.set_xlim(0, 500)
        ax.set_ylim(0, 500)
        ax.set_aspect('equal')
        #ax.grid(True, alpha=0.3)
        ax.set_title('Survey Mission Planner - Draw Polygon', fontsize=14, fontweight='bold')
        ax.set_xlabel('X (canvas units)', fontsize=10)
        ax.set_ylabel('Y (canvas units)', fontsize=10)
        
        # Connect event handlers
        fig.canvas.mpl_connect('button_press_event', on_click)
        fig.canvas.mpl_connect('key_press_event', on_key)
        
        plt.tight_layout()
        plt.show()
        
        print("\n" + "="*60)
        print("Program ended.")
        print("="*60)

    

if __name__ == "__main__":
    main()

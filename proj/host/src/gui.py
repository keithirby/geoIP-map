import threading
import time
import random
import numpy as np
import geopandas as gpd
import geodatasets

import dearpygui.dearpygui as dpg
from shapely.geometry import Polygon, MultiPolygon

# Local Libraries we need 
from config import NATURALEARTH_LOWRES_PATH
from db import initalize_engines, get_geoip_session

# =============================
# 1) Load and preprocess country shapes
# =============================
print("Loading world polygons...")
world = gpd.read_file(NATURALEARTH_LOWRES_PATH)
print(world.head())
print(world.columns.tolist())



# Simplify polygons to reduce vertex count (important for performance!)
world["geometry"] = world["geometry"].simplify(0.05)

# Build dictionary: country_name -> list of polygon vertices
country_polygons = {}
print("Building country polygons from 'ADMIN' column (with simplification)...")
for _, row in world.iterrows():
    name = row["ADMIN"]
    geom = row["geometry"]

    # Simplify geometry for performance (tolerance controls smoothness)
    geom = geom.simplify(0.05, preserve_topology=True)

    if isinstance(geom, Polygon):
        polygons = [geom]
    elif isinstance(geom, MultiPolygon):
        polygons = list(geom.geoms)  # ✅ FIX: use .geoms instead of list(geom)
    else:
        continue  # skip weird geometry types

    country_polygons[name] = []
    for poly in polygons:
        if poly.is_empty:
            continue  # skip invalid polygons
        x, y = poly.exterior.xy
        country_polygons[name].append(list(zip(x, y)))

print(f"Loaded {len(country_polygons)} countries.")

   

print(f"Loaded {len(country_polygons)} countries.")

# =============================
# 2) DearPyGui setup
# =============================
all_x = np.concatenate([np.array([pt[0] for pt in poly])
                        for polys in country_polygons.values()
                        for poly in polys])
all_y = np.concatenate([np.array([pt[1] for pt in poly])
                        for polys in country_polygons.values()
                        for poly in polys])

x_min, x_max = all_x.min(), all_x.max()
y_min, y_max = all_y.min(), all_y.max()
bbox_width = x_max - x_min
bbox_height = y_max - y_min

# Transform function will now take canvas size dynamically
def transform_to_canvas(point, canvas_w, canvas_h, padding=50):
    x, y = point
    scale_x = (canvas_w - 2*padding) / bbox_width
    scale_y = (canvas_h - 2*padding) / bbox_height
    scale = min(scale_x, scale_y)
    x_new = (x - x_min) * scale + padding
    y_new = (y_max - y) * scale + padding  # flip y-axis
    return (x_new, y_new)

dpg.create_context()

# Initial sizes
control_panel_width = 250

# Create viewport first
dpg.create_viewport(title="Live Country Map", width=1200, height=800)
dpg.setup_dearpygui()

# Map drawlist placeholder
map_width, map_height = 900, 600

with dpg.window(label="Live Country Map", width=map_width+control_panel_width+20, height=map_height+50):
    with dpg.group(horizontal=True):
        # Map drawlist
        with dpg.drawlist(width=map_width, height=map_height) as map_drawlist:
            country_items = {}
            for country_name, polys in country_polygons.items():
                for poly in polys:
                    transformed_points = [transform_to_canvas(pt, map_width, map_height) for pt in poly]
                    item = dpg.draw_polygon(
                        points=transformed_points,
                        color=(255, 255, 255, 255),
                        fill=(200, 200, 200, 255),
                        thickness=1.0,
                        parent=map_drawlist
                    )
                    country_items.setdefault(country_name, []).append(item)

        # Control panel
        with dpg.group(horizontal=False, width=control_panel_width):
            dpg.add_text("Controls")
            # Filter input
            def filter_callback(sender, app_data, user_data):
                search_text = dpg.get_value(sender).lower()
                for country, items in country_items.items():
                    visible = search_text in country.lower()
                    for item in items:
                        dpg.configure_item(item, show=visible)
            dpg.add_input_text(label="Filter countries", callback=filter_callback, width=control_panel_width)
            
            # Color intensity slider
            color_settings = {"multiplier": 1.0}
            def color_multiplier_callback(sender, app_data, user_data):
                color_settings["multiplier"] = app_data
            dpg.add_slider_float(label="Color intensity", min_value=0.1, max_value=3.0,
                                 default_value=1.0, callback=color_multiplier_callback)

# Show viewport
dpg.show_viewport()

# Function to transform polygons based on current drawlist size
def transform_to_canvas_dynamic(point, drawlist_w, drawlist_h, padding=50):
    all_x = np.concatenate([np.array([pt[0] for pt in poly])
                            for polys in country_polygons.values() for poly in polys])
    all_y = np.concatenate([np.array([pt[1] for pt in poly])
                            for polys in country_polygons.values() for poly in polys])
    x_min, x_max = all_x.min(), all_x.max()
    y_min, y_max = all_y.min(), all_y.max()
    bbox_width = x_max - x_min
    bbox_height = y_max - y_min

    x, y = point
    scale_x = (drawlist_w - 2*padding) / bbox_width
    scale_y = (drawlist_h - 2*padding) / bbox_height
    scale = min(scale_x, scale_y)
    x_new = (x - x_min) * scale + padding
    y_new = (y_max - y) * scale + padding  # flip y-axis
    return (x_new, y_new)

# Resize handler
def resize_callback(sender, app_data):
    viewport_w = dpg.get_viewport_width() - control_panel_width - 20
    viewport_h = dpg.get_viewport_height() - 20
    dpg.configure_item(map_drawlist, width=viewport_w, height=viewport_h)

    # Recompute transformed points for each polygon
    for country, items in country_items.items():
        polys = country_polygons[country]
        for poly, item in zip(polys, items):
            transformed_points = [transform_to_canvas_dynamic(pt, viewport_w, viewport_h) for pt in poly]
            dpg.configure_item(item, points=transformed_points)

# Bind the handler
dpg.set_viewport_resize_callback(resize_callback)

dpg.start_dearpygui()
dpg.destroy_context()

# =============================
# 3) Background thread to simulate live DB updates
# =============================
def live_update_loop():
    while dpg.is_dearpygui_running():
        for country, items in country_items.items():
            # Simulate frequency as a random number
            freq = random.random()

            # Map frequency -> color (red for high freq, green for low freq)
            r = int(255 * freq)
            g = int(255 * (1 - freq))
            color = (r, g, 100, 255)

            for item in items:
                dpg.configure_item(item, fill=color)

        time.sleep(0.5)  # sub-second updates (tune as needed)

# Start the background thread
threading.Thread(target=live_update_loop, daemon=True).start()


#initalize_engines()
#geoip_session = get_geoip_session()
#country_records = geoip_session.execute(QUERY_COUNTRIES_RECORD_STMT).fetchall()
#QUERY_COUNTRIES_RECORD_STMT = text(
#    "SELECT country_name FROM countries"
#)
#country_list = [(row[0], row[1]) for row in country_records]
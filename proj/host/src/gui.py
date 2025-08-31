import threading
import time
import random
import numpy as np
import geopandas as gpd
import geodatasets

import dearpygui.dearpygui as dpg
from shapely.geometry import Polygon, MultiPolygon

# Local Libraries we need 
from config import NATURALEARTH_LOWRES_PATH, COUNTRY_FIX_LIST
from db import initalize_engines, get_geoip_session


# Load stuff from the databases we need
from sqlalchemy import text
geoip_session = get_geoip_session()
QUERY_COUNTRIES_RECORD_STMT = text(
    "SELECT country_name, geoname_id FROM countries"
)
country_records = geoip_session.execute(QUERY_COUNTRIES_RECORD_STMT).fetchall()
country_list = [(row[0], row[1]) for row in country_records]

# =============================
# 1) Load and preprocess country shapes
# =============================
print("Loading world polygons...")
world = gpd.read_file(NATURALEARTH_LOWRES_PATH)
print(world.head())
print(world.columns.tolist())


# Convert to dictionary for easy lookup
country_fix_dict = dict(COUNTRY_FIX_LIST)

print("Fixing country names from country_fix_list...")
for idx, row in world.iterrows():
    country_name = row["ADMIN"]
    if country_name in country_fix_dict:
        fixed_name = country_fix_dict[country_name]
        world.at[idx, "ADMIN"] = fixed_name
        print(f"Fixed: {country_name} -> {fixed_name}")
print("Checking for matches between countries table and world map supported country polygons...")
for _, row in world.iterrows():
    country_name = row["ADMIN"]
    
    if country_name is None:
        print("ERROR: None value in world map")
        continue

    country_name_lower = country_name.lower()

    # Check for a match in country_list safely
    matched = False
    for listed_country, _ in country_list:
        if listed_country is None:  # skip None entries
            continue
        if country_name_lower == listed_country.lower():
            matched = True
            break

    if matched:
        print(f"Matched! {country_name}")
    else:
        print(f"ERROR: {country_name}")


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
initial_viewport_width = 1200
initial_viewport_height = 800
control_panel_width_ratio = 0.25  # 25% of viewport width for controls

# Dynamic transform function
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

# Create viewport
dpg.create_viewport(title="Live Country Map", width=initial_viewport_width, height=initial_viewport_height)
dpg.setup_dearpygui()

with dpg.window(label="Live Country Map", width=initial_viewport_width, height=initial_viewport_height):
    with dpg.group(horizontal=True):
        # Map drawlist
        with dpg.drawlist(width=int(initial_viewport_width*(1-control_panel_width_ratio)), 
                          height=initial_viewport_height) as map_drawlist:
            country_items = {}
            for country_name, polys in country_polygons.items():
                for poly in polys:
                    transformed_points = [transform_to_canvas_dynamic(pt,
                                                int(initial_viewport_width*(1-control_panel_width_ratio)),
                                                initial_viewport_height) for pt in poly]
                    item = dpg.draw_polygon(
                        points=transformed_points,
                        color=(255, 255, 255, 255),
                        fill=(200, 200, 200, 255),
                        thickness=1.0,
                        parent=map_drawlist
                    )
                    country_items.setdefault(country_name, []).append(item)

        # Control panel
        with dpg.child_window(width=int(initial_viewport_width*control_panel_width_ratio),
                      height=initial_viewport_height,
                      border=True) as control_panel:
            dpg.add_text("Controls")

            # Filter input
            # Commented out so I can work on trying to get 1 button working correctly
            #def filter_callback(sender, app_data, user_data):
            #    search_text = dpg.get_value(sender).lower()
            #    for country, items in country_items.items():
            #        visible = search_text in country.lower()
            #        for item in items:
            #            dpg.configure_item(item, show=visible)
            #
            #dpg.add_input_text(
            #    label="Filter countries",
            #    callback=filter_callback,
            #    width=int(initial_viewport_width*control_panel_width_ratio) - 20  # small padding
            #)

            # Color intensity slider
            color_settings = {"multiplier": 1.0}
            def color_multiplier_callback(sender, app_data, user_data):
                color_settings["multiplier"] = app_data

            dpg.add_slider_float(
                label="Color intensity",
                min_value=0.1,
                max_value=3.0,
                default_value=1.0,
                callback=color_multiplier_callback,
                width=int(initial_viewport_width*control_panel_width_ratio) - 20  # match input width
            )

# Show viewport
dpg.show_viewport()



# Viewport resize handler
def resize_callback(sender, app_data):
    viewport_w = dpg.get_viewport_width()
    viewport_h = dpg.get_viewport_height()

    # Adjust map and control panel widths and heights
    map_w = int(viewport_w * (1 - control_panel_width_ratio))
    map_h = viewport_h
    control_w = viewport_w - map_w
    control_h = viewport_h

    dpg.configure_item(map_drawlist, width=map_w, height=map_h)
    dpg.configure_item(control_panel, width=control_w, height=control_h)

    # Update all polygon points
    for country, items in country_items.items():
        polys = country_polygons[country]
        for poly, item in zip(polys, items):
            transformed_points = [transform_to_canvas_dynamic(pt, map_w, map_h) for pt in poly]
            dpg.configure_item(item, points=transformed_points)

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
        print("updating map data")
        time.sleep(0.5)  # sub-second updates (tune as needed)

# Start the background thread
threading.Thread(target=live_update_loop, daemon=True).start()




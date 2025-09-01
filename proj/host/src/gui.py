"""
@file seperate application for running the heat map GUI
"""
# Standard libraries we need
import threading
import time
import random
import numpy as np


# Package libraries we need
import geopandas as gpd
import dearpygui.dearpygui as dpg
from shapely.geometry import Polygon, MultiPolygon

# Local Libraries we need 
from config import NATURALEARTH_LOWRES_PATH, COUNTRY_FIX_LIST, QUERY_COUNTRIES_RECORD_STMT, QUERY_TUPLE_RECORD_STMT, PACKET_SUB_SEARCH_FREQ_STMT
from db import initalize_engines, get_geoip_session


# Load stuff from the databases dby.py file we need
geoip_session = get_geoip_session()
country_records = geoip_session.execute(QUERY_COUNTRIES_RECORD_STMT).fetchall()
country_list = [(row[0], row[1]) for row in country_records]


# Load and preprocess country shapes
print("Loading world polygons...")
world = gpd.read_file(NATURALEARTH_LOWRES_PATH)
print("polygons loaded ...")

# =============================
# -- List Initilzation setup --
# =============================
"""
@brief Go through the list of countries we can render from the `.shp` 
file and fix them from names that we have major IP block record for
"""
def fix_shp_file_country_names():
    # Convert to fix list to a dictonary to make lookup faster
    country_fix_dict = dict(COUNTRY_FIX_LIST)
    print("Fixing country names from country_fix_list...")
    # Go through every country the map supports
    for idx, row in world.iterrows():
        country_name = row["ADMIN"]
        # If we hit finding a match, replace
        if country_name in country_fix_dict:
            fixed_name = country_fix_dict[country_name]
            world.at[idx, "ADMIN"] = fixed_name
            print(f"Fixed: {country_name} -> {fixed_name}")


"""
@brief check that every country in the '.shp' file matches at least one name 
in our major IP block table
"""
def check_all_countries_match_block():
    print("Checking for matches between countries table and world map supported country polygons")
    for _, row in world.iterrows():
        country_name = row["ADMIN"]
        if country_name is None:
            # Country wasnt found log it to the console
            print("ERROR: None value in world map")
            continue
        country_name_lower = country_name.lower()
        # Check for a match in country_list
        matched = False
        for listed_country, _ in country_list:
            if listed_country is None:  # skip None entries
                continue
            if country_name_lower == listed_country.lower():
                matched = True
                break
        # Print the result
        if matched:
            print(f"Matched! {country_name}")
        else:
            print(f"ERROR: {country_name}")

# =============================
# ------- Map  setup ----------
# =============================
"""
@brief setup the polygon map from the `.shp` file 
for the countries to render it later
Returns: world GeoDataFrame, dictionary of country polygons
"""
def setup_country_polygons():
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
    return world, country_polygons

# =============================
# ------ DearPyGui setup ------
# =============================
"""
@brief Dynamically transform a geographic point to the drawlist coordinates.
In other words slowly update the guy elements like the map if we change the size of the window
"""
def transform_to_canvas_dynamic(point, polys, drawlist_w, drawlist_h, padding=50):
    
    all_x = np.concatenate([np.array([pt[0] for pt in poly]) for poly_set in polys.values() for poly in poly_set])
    all_y = np.concatenate([np.array([pt[1] for pt in poly]) for poly_set in polys.values() for poly in poly_set])
    x_min, x_max = all_x.min(), all_x.max()
    y_min, y_max = all_y.min(), all_y.max()
    bbox_width = x_max - x_min
    bbox_height = y_max - y_min

    x, y = point
    scale_x = (drawlist_w - 2*padding) / bbox_width
    scale_y = (drawlist_h - 2*padding) / bbox_height
    scale = min(scale_x, scale_y)
    x_new = (x - x_min) * scale + padding
    y_new = (y_max - y) * scale + padding
    return (x_new, y_new)

"""
@brief Dynamically transform a geographic point to the drawlist coordinates.
In other words slowly update the guy elements like the map if we change the size of the window
"""
def create_map_window(country_polygons, initial_viewport_width=1200, initial_viewport_height=800, control_panel_width_ratio=0.25):
    dpg.create_context()

    # Create viewport
    dpg.create_viewport(title="Live Country Map", width=initial_viewport_width, height=initial_viewport_height)
    dpg.setup_dearpygui()

    with dpg.window(label="Live Country Map", width=initial_viewport_width, height=initial_viewport_height):
        with dpg.group(horizontal=True):
            # Map drawlist
            map_w = int(initial_viewport_width * (1 - control_panel_width_ratio))
            map_h = initial_viewport_height
            with dpg.drawlist(width=map_w, height=map_h) as map_drawlist:
                country_items = {}
                for country_name, polys in country_polygons.items():
                    for poly in polys:
                        transformed_points = [transform_to_canvas_dynamic(pt, country_polygons, map_w, map_h) for pt in poly]
                        item = dpg.draw_polygon(
                            points=transformed_points,
                            color=(255, 255, 255, 255),
                            fill=(200, 200, 200, 255),
                            thickness=1.0,
                            parent=map_drawlist
                        )
                        country_items.setdefault(country_name, []).append(item)

            # Control panel
            control_w = initial_viewport_width - map_w
            control_h = initial_viewport_height
            with dpg.group(horizontal=False) as control_panel:
                dpg.add_text("Controls")
                color_settings = {"multiplier": 1.0}

                # Example slider
                def color_multiplier_callback(sender, app_data, user_data):
                    color_settings["multiplier"] = app_data
                dpg.add_slider_float(label="Color intensity", min_value=0.1, max_value=3.0,
                                     default_value=1.0, callback=color_multiplier_callback)

    return map_drawlist, control_panel, country_items


"""
@brief Function for reizing the geopanda map if we change the size of the DearPyGUI window
"""
def setup_resize_handler(map_drawlist, control_panel, country_items, country_polygons, control_panel_width_ratio=0.25):
    def resize_callback(sender, app_data):
        viewport_w = dpg.get_viewport_width()
        viewport_h = dpg.get_viewport_height()

        map_w = int(viewport_w * (1 - control_panel_width_ratio))
        map_h = viewport_h
        control_w = viewport_w - map_w
        control_h = viewport_h

        dpg.configure_item(map_drawlist, width=map_w, height=map_h)
        dpg.configure_item(control_panel, width=control_w, height=control_h)

        # Update polygon points
        for country, items in country_items.items():
            polys = country_polygons[country]
            for poly, item in zip(polys, items):
                transformed_points = [transform_to_canvas_dynamic(pt, country_polygons, map_w, map_h) for pt in poly]
                dpg.configure_item(item, points=transformed_points)

    dpg.set_viewport_resize_callback(resize_callback)

"""
@brief start and destroy the guy after all the setup is done
"""
def run_gui():
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()

# =============================
# ------ Geopanda map updater--
# =============================
# Function to fetch frequency for a given country name
def get_country_frequency(country_name):
    with get_geoip_session() as conn:
        # 1) Fetch the country's ID
        country_result = conn.execute(QUERY_TUPLE_RECORD_STMT, {"country_name": country_name}).fetchone()
        
        if not country_result:
            print(f"ERROR: Country '{country_name}' not found in countries table.")
            return None
        
        geoname_id = country_result[0]
        print(f"Found country '{country_name}' with ID {geoname_id}.")

        # 2) Fetch the frequency from packets table
        packet_result = conn.execute(PACKET_SUB_SEARCH_FREQ_STMT, {"geoname_id": geoname_id}).fetchone()
        
        if not packet_result:
            print(f"No packet record found for country ID {geoname_id}.")
            return None
        
        frequency = packet_result[0]
        print(f"Frequency for country '{country_name}' is {frequency}.")
        return frequency

def live_update_loop(country_items, color_multiplier=1.0, freq_max=1.0):
    while dpg.is_dearpygui_running():
        for country, items in country_items.items():
            freq = get_country_frequency(country)

            if freq is None:
                continue

            # Normalize to 0–1
            norm_freq = min(freq / freq_max, 1.0)

            # Wide gradient: green -> yellow -> red
            r = int(255 * norm_freq * color_multiplier)
            g = int(255 * (1 - norm_freq) * color_multiplier)
            b = 0  # keep pure warm/cool tones for a clear gradient
            color = (r, g, b, 255)

            for item in items:
                dpg.configure_item(item, fill=color)

        time.sleep(0.5)
    


def main(): 
    fix_shp_file_country_names()
    check_all_countries_match_block()
    # 1) Load and simplify polygons
    world, country_polygons = setup_country_polygons()
    print("polygons done")
    # 2) Create map window
    map_drawlist, control_panel, country_items = create_map_window(country_polygons)
    print("finished map windows")
    # 3) Setup viewport resize handler
    setup_resize_handler(map_drawlist, control_panel, country_items, country_polygons)
    print("resize setup")
    # Setup the map updater
    threading.Thread(target=live_update_loop, args=(country_items,), daemon=True).start()
    print("threading started")
    # 4) Run the GUI
    run_gui()


if __name__ == "__main__":
    main()




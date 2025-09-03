"""
@file seperate application for running the heat map GUI
"""
# Standard libraries we need
import threading
import time
import random
import numpy as np
import colorsys



# Package libraries we need
import geopandas as gpd
import dearpygui.dearpygui as dpg
from shapely.geometry import Polygon, MultiPolygon

# Local Libraries we need 
from config import NATURALEARTH_LOWRES_PATH, COUNTRY_FIX_LIST, QUERY_COUNTRIES_RECORD_STMT, QUERY_TUPLE_RECORD_STMT, PACKET_SUB_SEARCH_FREQ_STMT
from db import initalize_engines, get_geoip_session, PACKET_LOCK, reset_packet_table
from gui_controls import (
    create_sniffer_toggle,
    create_reset_button,
    create_timer_controls
)
from thread_control import (
    main,
    reset_config,
    start_sniffer_thread,
    stop_sniffer_thread,
    start_reset_thread,
    stop_reset_thread
)


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
    #print("Fixing country names from country_fix_list...")
    # Go through every country the map supports
    for idx, row in world.iterrows():
        country_name = row["ADMIN"]
        # If we hit finding a match, replace
        if country_name in country_fix_dict:
            fixed_name = country_fix_dict[country_name]
            world.at[idx, "ADMIN"] = fixed_name
            #print(f"Fixed: {country_name} -> {fixed_name}")


"""
@brief check that every country in the '.shp' file matches at least one name 
in our major IP block table
"""
def check_all_countries_match_block():
    #print("Checking for matches between countries table and world map supported country polygons")
    # Load stuff from the databases dby.py file we need
    geoip_session = get_geoip_session()
    country_records = geoip_session.execute(QUERY_COUNTRIES_RECORD_STMT).fetchall()
    country_list = [(row[0], row[1]) for row in country_records]
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
        #if matched:
        #    print(f"Matched! {country_name}")
        #else:
        #    print(f"ERROR: {country_name}")

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
            polygons = list(geom.geoms)
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
def transform_to_canvas_dynamic(point, polys, drawlist_w, drawlist_h, padding=0):
    
    all_x = np.concatenate([np.array([pt[0] for pt in poly]) for poly_set in polys.values() for poly in poly_set])
    all_y = np.concatenate([np.array([pt[1] for pt in poly]) for poly_set in polys.values() for poly in poly_set])
    x_min, x_max = all_x.min(), all_x.max()
    y_min, y_max = all_y.min(), all_y.max()
    bbox_width = x_max - x_min
    bbox_height = y_max - y_min

    # Scale to fill entire drawlist
    scale_x = drawlist_w / bbox_width
    scale_y = drawlist_h / bbox_height
    scale = min(scale_x, scale_y)

    # Center map in the drawlist
    x_offset = (drawlist_w - bbox_width * scale) / 2
    y_offset = (drawlist_h - bbox_height * scale) / 2

    x, y = point
    x_new = (x - x_min) * scale + x_offset
    y_new = (y_max - y) * scale + y_offset   # flip Y to match canvas
    return (x_new, y_new)

"""
@brief Dynamically transform a geographic point to the drawlist coordinates and add it to our GUI window.
Plus initalize all our interactable elements like buttons.
"""
def create_window_gui(country_polygons, initial_viewport_width=1920, initial_viewport_height=1080, control_panel_height_ratio=0.25):
    dpg.create_context()
    # Create viewport
    dpg.create_viewport(title="Packet Map", width=initial_viewport_width, height=initial_viewport_height)
    # Use this to change the guis colors
    dpg.set_viewport_clear_color((255, 255, 255, 255))  # White GUI
    dpg.setup_dearpygui()

    with dpg.window(label="Live Country Map", width=initial_viewport_width, height=initial_viewport_height):
        # Vertical layout: map on top, controls below
        with dpg.group(horizontal=False):
            # Map drawlist (take most of the window height)
            map_h = int(initial_viewport_height * (1 - control_panel_height_ratio))
            map_w = initial_viewport_width
            with dpg.drawlist(width=map_w, height=map_h) as map_drawlist:
                # Draw a ocean rectangle backgroudn onto the GUI 
                # --- Draw ocean background first ---
                dpg.draw_rectangle(
                    pmin=(0, 0),
                    pmax=(map_w, map_h),
                    color=(0, 0, 0, 0),             # no border
                    fill=(173, 216, 230, 255)       # light blue fill for ocean
                )
                # Draw all the countries onto the GUI 
                country_items = {}
                for country_name, polys in country_polygons.items():
                    for poly in polys:
                        transformed_points = [
                            transform_to_canvas_dynamic(pt, country_polygons, map_w, map_h) for pt in poly
                        ]
                        # Use this to change the map polygons
                        item = dpg.draw_polygon(
                            points=transformed_points,
                            color=(0, 0, 0, 255),              # black outlines
                            fill=(200, 200, 200, 255),        # light gray fill
                            thickness=1.5,                    # slightly thicker borders
                            parent=map_drawlist
                        )
                        country_items.setdefault(country_name, []).append(item)

            # Control panel in a tab bar below the map now
            control_h = initial_viewport_height - map_h
            # Color theme for the control panel
            with dpg.theme() as control_panel_theme:
                with dpg.theme_component(dpg.mvAll):
                    dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (80, 80, 80, 255))     # matte grey background
                    dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (80, 80, 80, 255))      # child windows same grey
                    dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))      # white text
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (100, 100, 100, 255))   # input/slider backgrounds
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (120, 120, 120, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (140, 140, 140, 255))
            
            with dpg.tab_bar():
                with dpg.tab(label="Control Panel"):
                    with dpg.group(horizontal=False) as control_panel:
                        # Bind the matte grey theme to the control panel
                        dpg.bind_item_theme(control_panel, control_panel_theme)
            
                        # Title text will now follow the theme (white)
                        dpg.add_text("Controls")  
                        
                        with dpg.table(header_row=False, borders_innerV=False, borders_innerH=False):
                            dpg.add_table_column()  # single column for stacking

                            with dpg.table_row():
                                with dpg.group(horizontal=False):
                                   sniffer_state, sniffer_drawlist, toggle_draw_fn = create_sniffer_toggle(dpg.last_item())

                            with dpg.table_row():
                                with dpg.group(horizontal=False):
                                    create_reset_button(dpg.last_item(), sniffer_state, sniffer_drawlist, toggle_draw_fn)

                            with dpg.table_row():
                                with dpg.group(horizontal=False):
                                    create_timer_controls(dpg.last_item(), reset_config)

            
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
    with PACKET_LOCK:
        with get_geoip_session() as conn:
            # 1) Fetch the country's ID
            country_result = conn.execute(QUERY_TUPLE_RECORD_STMT, {"country_name": country_name}).fetchone()

            if not country_result:
                return None
                #print(f"ERROR: Country '{country_name}' not found in countries table.")
                
            geoname_id = country_result[0]
            #print(f"Found country '{country_name}' with ID {geoname_id}.")

            # 2) Fetch the frequency from packets table
            packet_result = conn.execute(PACKET_SUB_SEARCH_FREQ_STMT, {"geoname_id": geoname_id}).fetchone()

            if not packet_result:
                #print(f"No packet record found for country ID {geoname_id}.")
                return 0

            frequency = packet_result[0]
            #print(f"Frequency for country '{country_name}' is {frequency}.")
            return frequency

def live_update_loop(country_items, freq_max=10.0):
    while dpg.is_dearpygui_running():
        for country, items in country_items.items():
            freq = get_country_frequency(country)
            if freq is None:
                continue
            
            #print(f"Updating {country} for {freq}")

            if freq == 0:
                # No data -> white
                color = (255, 255, 255, 255)
            else:
                # Normalize to 0–1 range
                step = min(freq / freq_max, 1.0)

                # Interpolate hue: green (120°) → red (0°)
                hue = (120 * (1 - step)) / 360.0
                r_f, g_f, b_f = colorsys.hsv_to_rgb(hue, 1, 1)

                # Convert floats to 0-255
                r, g, b = int(r_f * 255), int(g_f * 255), int(b_f * 255)
                color = (r, g, b, 255)

            # Update polygons
            for item in items:
                dpg.configure_item(item, fill=color)

        time.sleep(1)
    


def main(): 
    fix_shp_file_country_names()
    check_all_countries_match_block()
    # 1) Load and simplify polygons
    world, country_polygons = setup_country_polygons()
    print("polygons done")
    # 2) Create map window
    map_drawlist, control_panel, country_items = create_window_gui(country_polygons)
    print("finished map windows")
    # 3) Start all the callback (buttons and interactable elements) threads for the GUI
    
    # 3) Setup viewport resize handler, this one is ambitious and mostly doesnt work, 
    # Easiest way to get the correct window size is set the dimension parameters in 
    # create_window_gui
    setup_resize_handler(map_drawlist, control_panel, country_items, country_polygons)
    print("resize setup")
    # Setup the map updater
    threading.Thread(target=live_update_loop, args=(country_items,10), daemon=True).start()
    print("threading started")
    # 4) Run the GUI
    run_gui()


if __name__ == "__main__":
    main()




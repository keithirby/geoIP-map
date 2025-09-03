# Package libraries we need
import dearpygui.dearpygui as dpg


# Local libraries we need
from thread_control import (
    main,
    reset_config,
    start_sniffer_thread,
    stop_sniffer_thread,
    start_reset_thread,
    stop_reset_thread
)
from db import reset_packet_table

# shared globals for keeping like buttons the same size
TOGGLE_WIDTH = 120
TOGGLE_HEIGHT = 40
HANDLE_RADIUS = 15
PADDING = 5  # space from left/right edges

# Shared global Colors
COLOR_ON = (150, 50, 255, 255)      # Purple (ON state)
COLOR_OFF = (180, 180, 200, 255)    # Grey (OFF state)
COLOR_RESET = (100, 100, 100, 255)  # Default reset button color


#--------------------------------------------------------
#---------------- Vertical column 1 controls ------------
#--------------------------------------------------------
"""
@brief sniffer toggle switch to start and stop sniffing for packets
"""
def create_sniffer_toggle(parent):
    sniffer_state = {"running": False}

    def draw_sniffer_toggle(drawlist):
        dpg.delete_item(drawlist, children_only=True)
        is_on = sniffer_state["running"]

        # Define toggles for `handle` (button in the center of toggle switch)
        bg_color = COLOR_ON if is_on else COLOR_OFF
        text_color = (255, 255, 255, 255) if is_on else (50, 50, 50, 255)
        label = "ON" if is_on else "OFF"

        # Dynamically compute handle position so its not off center
        handle_x = (TOGGLE_WIDTH - PADDING - HANDLE_RADIUS*2) if is_on else PADDING

        # Background pill shape the 'handle' sits in
        dpg.draw_rectangle(
            (0, 0), (TOGGLE_WIDTH, TOGGLE_HEIGHT),
            fill=bg_color, color=bg_color, rounding=TOGGLE_HEIGHT // 2,
            parent=drawlist
        )
        # Handle circle
        dpg.draw_circle(
            center=(handle_x + HANDLE_RADIUS, TOGGLE_HEIGHT // 2),
            radius=HANDLE_RADIUS,
            fill=(255, 255, 255, 255),
            parent=drawlist
        )
        # Label
        dpg.draw_text(
            (TOGGLE_WIDTH // 2 - 12, TOGGLE_HEIGHT // 2 - 8),
            label, size=16, color=text_color, parent=drawlist
        )

    def toggle_sniffer(_, app_data):
        sniffer_state["running"] = not sniffer_state["running"]
        if sniffer_state["running"]:
            start_sniffer_thread()
        else:
            stop_sniffer_thread()
        draw_sniffer_toggle(sniffer_drawlist)

    with dpg.drawlist(width=TOGGLE_WIDTH, height=TOGGLE_HEIGHT, parent=parent) as sniffer_drawlist:
        draw_sniffer_toggle(sniffer_drawlist)
        with dpg.item_handler_registry() as handler:
            dpg.add_item_clicked_handler(callback=toggle_sniffer)
        dpg.bind_item_handler_registry(sniffer_drawlist, handler)

    return sniffer_state, sniffer_drawlist



"""
@brief reset button for our gui that resets the gradient color of countries
"""
def create_reset_button(parent, sniffer_state, sniffer_drawlist):
    # Define how the reset button should like when its NOT in use (not clicked)
    def redraw_sniffer_off():
        dpg.delete_item(sniffer_drawlist, children_only=True)
        dpg.draw_rectangle(
            (0, 0), (TOGGLE_WIDTH, TOGGLE_HEIGHT),
            fill=COLOR_OFF, color=COLOR_OFF,
            rounding=TOGGLE_HEIGHT // 2, parent=sniffer_drawlist
        )
        dpg.draw_circle(
            center=(PADDING + HANDLE_RADIUS, TOGGLE_HEIGHT // 2),
            radius=HANDLE_RADIUS,
            fill=(255, 255, 255, 255),
            parent=sniffer_drawlist
        )
        dpg.draw_text(
            (TOGGLE_WIDTH // 2 - 12, TOGGLE_HEIGHT // 2 - 8),
            "OFF", size=16, color=(50, 50, 50, 255), parent=sniffer_drawlist
        )

    # define how the reset button should look when its clicked (flash purple like toggle)
    def reset_callback(_, app_data):
        stop_sniffer_thread()
        reset_packet_table()
        sniffer_state["running"] = False
        redraw_sniffer_off()

        # Temporarily flash button purple
        dpg.delete_item(reset_drawlist, children_only=True)
        dpg.draw_rectangle(
            (0, 0), (TOGGLE_WIDTH, TOGGLE_HEIGHT),
            fill=COLOR_ON, color=COLOR_ON,
            rounding=TOGGLE_HEIGHT // 2, parent=reset_drawlist
        )
        dpg.draw_text(
            (TOGGLE_WIDTH // 2 - 25, TOGGLE_HEIGHT // 2 - 8),
            "RESET", size=16, color=(255, 255, 255, 255), parent=reset_drawlist
        )

        # Schedule to redraw back to its original state after 0.3s 
        def reset_back_to_normal():
            dpg.delete_item(reset_drawlist, children_only=True)
            dpg.draw_rectangle(
                (0, 0), (TOGGLE_WIDTH, TOGGLE_HEIGHT),
                fill=COLOR_RESET, color=COLOR_RESET,
                rounding=TOGGLE_HEIGHT // 2, parent=reset_drawlist
            )
            dpg.draw_text(
                (TOGGLE_WIDTH // 2 - 25, TOGGLE_HEIGHT // 2 - 8),
                "RESET", size=16, color=(255, 255, 255, 255), parent=reset_drawlist
            )
        dpg.set_frame_callback(dpg.get_frame_count() + 18, reset_back_to_normal)  # ≈0.3s at 60fps

    # Styled reset button using drawlist so its the same shape as the toggle switch
    with dpg.drawlist(width=TOGGLE_WIDTH, height=TOGGLE_HEIGHT, parent=parent) as reset_drawlist:
        dpg.draw_rectangle(
            (0, 0), (TOGGLE_WIDTH, TOGGLE_HEIGHT),
            fill=COLOR_RESET, color=COLOR_RESET,
            rounding=TOGGLE_HEIGHT // 2, parent=reset_drawlist
        )
        dpg.draw_text(
            (TOGGLE_WIDTH // 2 - 25, TOGGLE_HEIGHT // 2 - 8),
            "RESET", size=16, color=(255, 255, 255, 255), parent=reset_drawlist
        )
        with dpg.item_handler_registry() as handler:
            dpg.add_item_clicked_handler(callback=reset_callback)
        dpg.bind_item_handler_registry(reset_drawlist, handler)


"""
@brief timer control text box that defines how often to automatically reset the country gradients
"""
def create_timer_controls(parent, reset_config):
    dpg.add_separator(parent=parent)
    dpg.add_text("Reset Timer", parent=parent)

    # Use input_text to strictly control width/characters
    def timer_input_callback(sender, app_data):
        try:
            value = int(app_data)
            if value < 5:
                value = 5
            elif value > 3600:
                value = 3600
            reset_config["timer"] = value
            dpg.set_value(sender, str(value))  # enforce bounds visually
        except ValueError:
            dpg.set_value(sender, str(reset_config["timer"]))

    dpg.add_input_text(
        label="Interval (sec)",
        default_value=str(reset_config["timer"]),
        width=60,               # fixed width (~4 chars wide)
        callback=timer_input_callback,
        decimal=True,           # allow only numbers
        parent=parent
    )

    dpg.add_checkbox(
        label="Enable Auto Reset",
        default_value=reset_config["enabled"],
        callback=lambda s, a: reset_config.update({"enabled": a}),
        parent=parent
    )
#--------------------------------------------------------
#---------------- Vertical column 2 controls ------------
#--------------------------------------------------------
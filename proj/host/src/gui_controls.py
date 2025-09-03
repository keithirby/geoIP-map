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

# Global for controlling the sniffer between the listen mode toggle and reset button
RESET_IN_PROGRESS = False  # global



#--------------------------------------------------------
#---------------- Vertical column 1 controls ------------
#--------------------------------------------------------
"""
@brief sniffer toggle switch to start and stop sniffing for packets
"""
def create_sniffer_toggle(parent):
    sniffer_state = {"running": False}

    # Function to draw the toggle UI
    def toggle_draw_fn(drawlist, state):
        dpg.delete_item(drawlist, children_only=True)
        is_on = state["running"]
        bg_color   = COLOR_ON if is_on else COLOR_OFF
        text_color = (255, 255, 255, 255) if is_on else (50, 50, 50, 255)
        label      = "ON" if is_on else "OFF"
        handle_x   = (TOGGLE_WIDTH - PADDING - HANDLE_RADIUS*2) if is_on else PADDING

        # Draw toggle background
        dpg.draw_rectangle(
            (0, 0), (TOGGLE_WIDTH, TOGGLE_HEIGHT),
            fill=bg_color, color=bg_color, rounding=TOGGLE_HEIGHT // 2,
            parent=drawlist
        )
        # Draw handle
        dpg.draw_circle(
            center=(handle_x + HANDLE_RADIUS, TOGGLE_HEIGHT // 2),
            radius=HANDLE_RADIUS, fill=(255, 255, 255, 255), parent=drawlist
        )
        # Draw label
        dpg.draw_text(
            (TOGGLE_WIDTH // 2 - 12, TOGGLE_HEIGHT // 2 - 8),
            label, size=16, color=text_color, parent=drawlist
        )

    # Click handler for toggle
    def _on_click(sender, app_data, user_data):
        state, drawlist = user_data
        new_running = not state["running"]

        # Start/stop sniffer based on new state
        if new_running and not state["running"]:
            start_sniffer_thread()
        elif not new_running and state["running"]:
            stop_sniffer_thread()

        state["running"] = new_running
        toggle_draw_fn(drawlist, state)

    # Draw toggle UI
    with dpg.group(horizontal=False, parent=parent):
        dpg.add_text("Listen Mode")
        with dpg.drawlist(width=TOGGLE_WIDTH, height=TOGGLE_HEIGHT) as sniffer_drawlist:
            toggle_draw_fn(sniffer_drawlist, sniffer_state)

        # Bind click handler
        with dpg.item_handler_registry() as handler:
            dpg.add_item_clicked_handler(callback=_on_click, user_data=(sniffer_state, sniffer_drawlist))
        dpg.bind_item_handler_registry(sniffer_drawlist, handler)

    return sniffer_state, sniffer_drawlist, toggle_draw_fn

"""
@brief reset button for our gui that resets the gradient color of countries
"""
def create_reset_button(parent, sniffer_state, sniffer_drawlist, toggle_draw_fn):
    """
    Create a Reset button that stops the sniffer and resets the toggle.
    """
    def reset_callback(_, app_data):
        # Stop sniffer thread if running
        stop_sniffer_thread()

        # Update state and redraw toggle OFF
        sniffer_state["running"] = False
        toggle_draw_fn(sniffer_drawlist, sniffer_state)

        # Reset packet table
        reset_packet_table()

        # Flash reset button visually
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

        # Schedule reset button back to normal
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

        dpg.set_frame_callback(dpg.get_frame_count() + 18, reset_back_to_normal)

    # Draw reset button
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
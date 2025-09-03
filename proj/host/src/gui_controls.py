import dearpygui.dearpygui as dpg

"""
@brief sniffer toggle switch to start and stop sniffing for packets
"""
def create_sniffer_toggle(parent):
    """Create a custom ON/OFF toggle for starting/stopping the sniffer."""
    sniffer_state = {"running": False}

    def draw_sniffer_toggle(drawlist):
        dpg.delete_item(drawlist, children_only=True)
        is_on = sniffer_state["running"]
        bg_color = (150, 50, 255, 255) if is_on else (180, 180, 200, 255)
        text_color = (255, 255, 255, 255) if is_on else (50, 50, 50, 255)
        handle_x = 65 if is_on else 5
        label = "ON" if is_on else "OFF"

        dpg.draw_rectangle((0, 0), (120, 40), fill=bg_color, color=bg_color, rounding=20, parent=drawlist)
        dpg.draw_circle(center=(handle_x + 15, 20), radius=15, fill=(255, 255, 255, 255), parent=drawlist)
        dpg.draw_text((45, 12), label, size=16, color=text_color, parent=drawlist)

    def toggle_sniffer(sender, app_data, user_data):
        if sniffer_state["running"]:
            stop_sniffer_thread()
            sniffer_state["running"] = False
        else:
            start_sniffer_thread()
            sniffer_state["running"] = True
        draw_sniffer_toggle(user_data["drawlist"])

    with dpg.drawlist(width=120, height=40, parent=parent) as sniffer_drawlist:
        draw_sniffer_toggle(sniffer_drawlist)

    dpg.add_button(label="", width=120, height=40, callback=toggle_sniffer,
                   user_data={"drawlist": sniffer_drawlist},
                   tag="sniffer_toggle_button", parent=parent)

    return sniffer_state, sniffer_drawlist



"""
@brief reset button for our gui that resets the gradients of countries
"""
def create_reset_button(parent, sniffer_state, sniffer_drawlist):
    def reset_callback():
        stop_sniffer_thread()
        reset_packet_table()
        sniffer_state["running"] = False
        # redraw toggle in OFF state
        dpg.delete_item(sniffer_drawlist, children_only=True)
        dpg.draw_rectangle((0, 0), (120, 40), fill=(180, 180, 200, 255),
                           color=(180, 180, 200, 255), rounding=20, parent=sniffer_drawlist)
        dpg.draw_circle(center=(5 + 15, 20), radius=15, fill=(255, 255, 255, 255), parent=sniffer_drawlist)
        dpg.draw_text((45, 12), "OFF", size=16, color=(50, 50, 50, 255), parent=sniffer_drawlist)
        print("[Reset] Database reset and sniffer stopped.")
    dpg.add_button(label="Reset", callback=reset_callback, parent=parent)


"""
@brief timer control text box that defines how often to automatically reset the country gradients
"""
def create_timer_controls(parent, reset_config):
    dpg.add_separator(parent=parent)
    dpg.add_text("Reset Timer", parent=parent)
    dpg.add_input_int(
        label="Interval (sec)", default_value=reset_config["timer"],
        min_value=5, max_value=3600,
        callback=lambda s, a: reset_config.update({"timer": a}),
        step=1, parent=parent
    )
    dpg.add_checkbox(
        label="Enable Auto Reset", default_value=reset_config["enabled"],
        callback=lambda s, a: reset_config.update({"enabled": a}),
        parent=parent
    )
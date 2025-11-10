def on_start(core):
    print("[weather] started")

def get_weather(slots):
    # slots is a dict; plugin is free to interpret
    city = None
    if isinstance(slots, dict):
        city = slots.get('city') or slots.get('location')
    if not city:
        city = "Nowhere"
    return {"city": city, "forecast": "sunny", "temp_c": 22}

def on_stop():
    print("[weather] stopped")
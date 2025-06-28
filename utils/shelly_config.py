# Unified configuration for Shelly UNI and Shelly X MOD1 devices
shelly_uni_devices = {
    "washer_1": {"ip": "192.168.1.101", "input_status": "/status/input/0", "relay_control": "/relay/0"},
    #"washer_2": {"ip": "192.168.1.102", "input_status": "/status/input/0", "relay_control": "/relay/0"},
    "dryer_1": {"ip": "192.168.1.103", "input_status": "/status/input/0", "relay_control": "/relay/0"},
    #"dryer_2": {"ip": "192.168.1.104", "input_status": "/status/input/0", "relay_control": "/relay/0"}
}

# Configuration for Shelly X MOD1 controlling buttons and LEDs for all devices
shelly_x_mod1 = {
    "ip": "192.168.1.105",
    "button_endpoints": {
        "washer_1": "/status/input/0",
        #"washer_2": "/status/input/1",
        "dryer_1": "/status/input/2",
        #"dryer_2": "/status/input/3"
    },
    "led_endpoints": {
        "washer_1": "/relay/0",
        #"washer_2": "/relay/1",
        "dryer_1": "/relay/2",
        #"dryer_2": "/relay/3"
    }
}
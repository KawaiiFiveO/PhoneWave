# sip-call-handler/hardware_control/smart_plug.py

import requests
from config import SMART_PLUG_BASE_URL

def _send_command(command):
    """Sends a command to the smart plug."""
    try:
        # The command is sent as a URL parameter, e.g., ?cmnd=Power On
        response = requests.get(SMART_PLUG_BASE_URL, params={"cmnd": command})
        response.raise_for_status()  # Raise an exception for bad status codes
        print(f"Smart plug command '{command}' sent successfully.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to smart plug: {e}")
        return False

def turn_on():
    """Sends the 'Power On' command."""
    return _send_command("Power On")

def turn_off():
    """Sends the 'Power Off' command."""
    return _send_command("Power Off")
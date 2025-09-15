# sip-call-handler/main.py

import time
import threading
import config
from sip_handler.sip_client import SipClient
from hardware_control import smart_plug
from hardware_control.oled_display import oled

# --- Global state variables for timer and threads ---
plug_timer = None
display_thread = None
stop_display_event = threading.Event()

def cleanup_timer_and_threads():
    """Stop any active timer and display thread."""
    global plug_timer, display_thread
    if plug_timer:
        plug_timer.cancel()
        plug_timer = None
        print("Plug timer cancelled.")
    
    if display_thread:
        stop_display_event.set()
        display_thread.join() # Wait for thread to finish
        display_thread = None
        print("Display thread stopped.")

def plug_off_task():
    """Task to be executed when the timer expires."""
    print("Timer expired. Turning plug OFF.")
    smart_plug.turn_off()
    oled.display_message("Timer Finished", "Plug is OFF")
    cleanup_timer_and_threads()

def update_display_countdown(total_duration):
    """Thread target to update the OLED with a countdown."""
    start_time = time.time()
    while not stop_display_event.is_set():
        elapsed = time.time() - start_time
        remaining = int(total_duration - elapsed)
        if remaining < 0:
            break
        oled.update_countdown(remaining)
        time.sleep(1)

def handle_dtmf(duration_str):
    """Callback for when a full DTMF sequence (e.g., '120#') is received."""
    global plug_timer, display_thread

    print(f"DTMF sequence received: {duration_str}")
    
    try:
        duration_seconds = int(duration_str)
        if duration_seconds <= 0:
            raise ValueError("Duration must be positive.")
    except ValueError:
        print(f"Invalid duration: {duration_str}")
        oled.display_message("Invalid Time", duration_str)
        return

    # Clean up any previous timers before starting a new one
    cleanup_timer_and_threads()

    print(f"Turning plug ON for {duration_seconds} seconds.")
    if smart_plug.turn_on():
        # Start the timer to turn the plug off later
        plug_timer = threading.Timer(duration_seconds, plug_off_task)
        plug_timer.start()

        # Start the thread to update the display
        stop_display_event.clear()
        display_thread = threading.Thread(target=update_display_countdown, args=(duration_seconds,))
        display_thread.start()
    else:
        oled.display_message("Plug Error", "Check connection")

def on_call_disconnect():
    """Callback for when the SIP call is disconnected."""
    print("Call disconnected. Cleaning up active timers.")
    cleanup_timer_and_threads()
    # If the plug was on, turn it off as a safety measure
    smart_plug.turn_off()
    oled.display_message("Call Ended", "Plug is OFF")
    time.sleep(5) # Display message for a bit
    oled.display_message("System Ready", "Waiting for call...")

def main():
    """Main application function."""
    oled.display_message("System Starting...")
    
    sip_client = SipClient(
        config, 
        dtmf_callback=handle_dtmf,
        disconnect_callback=on_call_disconnect
    )
    
    try:
        sip_client.start()
        oled.display_message("System Ready", "Waiting for call...")
        
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"A critical error occurred: {e}")
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        cleanup_timer_and_threads()
        sip_client.stop()
        smart_plug.turn_off() # Ensure plug is off on exit
        oled.clear()
        print("Program terminated.")

if __name__ == "__main__":
    main()
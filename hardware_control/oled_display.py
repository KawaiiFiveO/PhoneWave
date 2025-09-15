# sip-call-handler/hardware_control/oled_display.py

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont
import os

class OLEDController:
    def __init__(self):
        try:
            # Initialize I2C interface and SSD1306 device
            self.serial = i2c(port=1, address=0x3C)
            self.device = ssd1306(self.serial, height=32) # 128x32 display
            
            # Load a font
            font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'fonts', 'pixelmix.ttf'))
            # Fallback to a default font if custom one is not found
            if os.path.exists(font_path):
                 self.font_small = ImageFont.truetype(font_path, 8)
                 self.font_large = ImageFont.truetype(font_path, 16)
            else:
                 self.font_small = ImageFont.load_default()
                 self.font_large = ImageFont.load_default()

            print("OLED display initialized successfully.")
        except Exception as e:
            print(f"Could not initialize OLED display: {e}")
            self.device = None

    def display_message(self, line1, line2=""):
        if not self.device: return
        with canvas(self.device) as draw:
            draw.text((0, 0), line1, font=self.font_small, fill="white")
            draw.text((0, 16), line2, font=self.font_small, fill="white")

    def update_countdown(self, remaining_seconds):
        if not self.device: return
        mins, secs = divmod(remaining_seconds, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        
        with canvas(self.device) as draw:
            draw.text((0, 0), "PLUG IS ON", font=self.font_small, fill="white")
            # Center the large time string
            text_width, _ = draw.textsize(time_str, font=self.font_large)
            x_pos = (self.device.width - text_width) / 2
            draw.text((x_pos, 8), time_str, font=self.font_large, fill="white")

    def clear(self):
        if not self.device: return
        self.device.clear()

# Create a single instance to be used by the application
oled = OLEDController()
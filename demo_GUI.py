# -*- coding: utf-8 -*-
"""
Created on Wed Oct 15 09:46:31 2025
@author: jeans
"""
class DemoMonochromator:
    """Simuleert een monochromator voor testdoeleinden (zonder prints)."""
    
    def __init__(self):
        self.connected = True
        self.current_wl = 500

    def open(self):
        return True

    def close(self):
        return True

    def sync(self):
        return True

    def reset(self):
        return True

    def set_wavelength(self, wl):
        self.current_wl = wl
        return True

    def shutterPos(self, pos):
        return True

    def readConfig(self):
        # Stil — geen print
        return True

    def readAddress(self, section):
        # Stil — geen print
        return True


class DemoCamera:
    """Simuleert een live camera-feed voor demo- of testmodus (zonder prints)."""

    def __init__(self):
        self.streaming = False

    def start_live(self):
        self.streaming = True

    def stop_live(self):
        self.streaming = False

    def get_latest_frame(self):
        """Return een dummy grijs vlak als camera-frame."""
        import numpy as np
        if not self.streaming:
            return None
        return np.full((300, 300), 128, dtype=np.uint8)

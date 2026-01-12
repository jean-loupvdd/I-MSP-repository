# -*- coding: utf-8 -*-
"""
Created on Tue Oct 21 10:59:09 2025

@author: jeans
"""

from GUI_MSP import MSP_GUI

if __name__ == "__main__":
    import sys
    try:
        app = MSP_GUI()
    except KeyboardInterrupt:
        try:
            app.on_close()
        except:
            pass
        sys.exit(0)
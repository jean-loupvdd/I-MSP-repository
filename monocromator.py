from serial import Serial, PARITY_NONE, STOPBITS_TWO
from serial.tools import list_ports
from configparser import ConfigParser
import struct
import os
import numpy as np
from scipy.interpolate import CubicSpline
import time
from pathlib import Path

class Monocromator:

    connection = Serial()
    command_bytes = []

    RESET = [0x04, 0x02]
    AXIS = [0x0F, 0xF0]
    CPA = [0x59, 0x09, 0xFF, 0xFF, 0x20, 0x00]
    UPD = [0x01, 0x08]
    CALL = [0x74, 0x01]

    def __init__(self, port_name):
        self.connection = Serial()
        self.connection.baudrate = 115200
        self.connection.bytesize = 8
        self.connection.timeout = 0.1
        self.connection.write_timeout = 0.1
        self.connection.parity = PARITY_NONE
        self.connection.stopbits = STOPBITS_TWO
        self.connection.port = port_name

    def readAddress(self, type):
        files = []
        for r, d, f in os.walk(os.getcwd()):
            for file in f:
                if '.cfg' in file:
                    files.append(os.path.join(r, file))
        matching = [file for file in files if type in file][0]
        with open(matching) as file: lines = [line.rstrip() for line in file]

        self.DEV = int([line for line in lines if 'DEV' in line][0].split('\t')[2][1:], 16)
        self.DEV = 0b111111111 & self.DEV
        self.DEV = 0x2000 | self.DEV
        self.DEV = list(struct.unpack('BB', struct.pack('>H', self.DEV)))

        self.CMD = int([line for line in lines if 'CMD' in line][0].split('\t')[2][1:], 16)
        self.CMD = 0b111111111 & self.CMD
        self.CMD = 0x2000 | self.CMD
        self.CMD = list(struct.unpack('BB', struct.pack('>H', self.CMD)))

        self.PRM = int([line for line in lines if 'PRM' in line][0].split('\t')[2][1:], 16)
        self.PRM = 0b111111111 & self.PRM
        self.PRM = 0x2000 | self.PRM
        self.PRM = list(struct.unpack('BB', struct.pack('>H', self.PRM)))

        self.CPOS = int([line for line in lines if 'CPOS' in line][0].split('\t')[2][1:], 16)
        self.CPOS = 0b111111111 & self.CPOS
        self.CPOS = 0x2400 | self.CPOS
        self.CPOS = list(struct.unpack('BB', struct.pack('>H', self.CPOS)))

        self.SENDCODE = int([line for line in lines if 'SENDCODE' in line][0].split('\t')[2][1:], 16)
        self.SENDCODE = list(struct.unpack('BB', struct.pack('>H', self.SENDCODE)))

    def readConfig(self):
        config = ConfigParser()
        config.read(r'config.txt')

        
        self.shutter_open = int(config.get('device_functions', 'ShutterTuning')
                            .strip('"').split(',')[2].split(':')[2])
        self.shutter_close = int(config.get('device_functions', 'ShutterTuning')
                             .strip('"').split(',')[3].split(':')[2])
        
        print(self.shutter_close)
        print(self.shutter_open)
    
        filter_line = config.get('device_functions', 'FilterTuning').strip('"')
        filter_parts = filter_line.split(',')

        # Maak dictionary met naam → positie
        self.filter_positions = {}
        for part in filter_parts[2:]:  # sla "B, 100" over
            name, _, value = part.split(':')
            self.filter_positions[name.strip()] = int(value)
        
        print(self.filter_positions)
        
        return True
    def open(self):
        try:
            self.connection.open()
            return True
        except:
            return False
        
    def close(self):
        try:
            self.connection.close()
            return True
        except:
            return False

    def sync(self):
        for i in range(15):
            self.connection.write(b'\x0D')
            if self.connection.read(1) == b'\x0D': return True
        return False

    def cs(self):
        cs = sum(self.command_bytes)
        cs = list(struct.unpack('2B', struct.pack('H', cs)))
        self.command_bytes.append(cs[0])

    def reset(self):
        self.command_bytes = self.AXIS + self.RESET
        self.command_bytes.insert(0, len(self.command_bytes))
        self.cs()
        self.connection.write(self.command_bytes)
        if self.connection.read(1) == b'\x4F': return True
        return False

    def cpa(self):
        self.command_bytes = self.AXIS + self.CPA
        self.command_bytes.insert(0, len(self.command_bytes))
        self.cs()
        self.connection.write(self.command_bytes)
        if self.connection.read(1) == b'\x4F': return True
        return False
    
    def cpr(self):
        self.command_bytes = self.AXIS + self.CPR
        self.command_bytes.insert(0, len(self.command_bytes))
        self.cs()
        self.connection.write(self.command_bytes)
        if self.connection.read(1) == b'\x4F': return True
        return False

    def upd(self):
        self.command_bytes = self.AXIS + self.UPD
        self.command_bytes.insert(0, len(self.command_bytes))
        self.cs()
        self.connection.write(self.command_bytes)
        if self.connection.read(1) == b'\x4F': return True
        return False

    def cpos(self, position):
        self.command_bytes = self.AXIS + self.CPOS
        position_bytes = list(struct.unpack('4B', struct.pack('I', position)))
        position_bytes[0], position_bytes[1], position_bytes[2], position_bytes[3] = position_bytes[1], position_bytes[0], position_bytes[3], position_bytes[2]
        self.command_bytes += position_bytes
        self.command_bytes.insert(0, len(self.command_bytes))
        self.cs()
        self.connection.write(self.command_bytes)
        if self.connection.read(1) == b'\x4F': return True
        return False
    
    def dev(self, device):
        self.command_bytes = self.AXIS + self.DEV
        self.command_bytes += list(struct.unpack('2B', struct.pack('>H', device)))
        self.command_bytes.insert(0, len(self.command_bytes))
        self.cs()
        self.connection.write(self.command_bytes)
        if self.connection.read(1) == b'\x4F': return True
        return False
    
    def cmd(self, command):
        self.command_bytes = self.AXIS + self.CMD
        self.command_bytes += list(struct.unpack('2B', struct.pack('>H', command)))
        self.command_bytes.insert(0, len(self.command_bytes))
        self.cs()
        self.connection.write(self.command_bytes)
        if self.connection.read(1) == b'\x4F': return True
        return False
    
    def prm(self, parameter):
        self.command_bytes = self.AXIS + self.PRM
        position_bytes = list(struct.unpack('4B', struct.pack('I', parameter)))
        position_bytes[0], position_bytes[1], position_bytes[2], position_bytes[3] = position_bytes[1], position_bytes[0], position_bytes[3], position_bytes[2]
        self.command_bytes += position_bytes
        self.command_bytes.insert(0, len(self.command_bytes))
        self.cs()
        self.connection.write(self.command_bytes)
        print(bytes(self.command_bytes).hex())
        if self.connection.read(1) == b'\x4F': return True
        return False
    
    def sendcode(self):
        self.command_bytes = self.AXIS + self.CALL + self.SENDCODE
        self.command_bytes.insert(0, len(self.command_bytes))
        self.cs()
        self.connection.write(self.command_bytes)
        if self.connection.read(1) == b'\x4F': return True
        return False
    
    def positionAbs(self, position):
        if not self.cpa(): return False
        if not self.cpos(position): return False
        if not self.upd(): return False
        return True
    
    def positionRel(self, position):
        if not self.cpr(): return False
        if not self.cpos(position): return False
        if not self.upd(): return False
        
    def motor_reset(self):
        print("Resetting motor...")
        RESET_CMD = bytes.fromhex("040FF0040209")
        self.ser.write(RESET_CMD)
        time.sleep(0.5)
        self.motor_off()
        time.sleep(0.5)
    
    def shutterPos(self, state):
        if state == "open":
            prm_value = self.shutter_open
            cmd_value = 1   # OPEN_POS_SET
        elif state == "close":
            prm_value = self.shutter_close
            cmd_value = 0   # CLOSE_POS_SET
        else:
            return False  # ongeldige parameter

        if not self.dev(1): return False      # device 1 = shutter
        if not self.cmd(cmd_value): return False
        if not self.prm(prm_value): return False
        if not self.sendcode(): return False

        return True


    
    def filterPos(self, filter_name, slot_number=1):
       
        if not 1 <= slot_number <= 4:
            print("Ongeldig slotnummer")
            return False
        if not self.dev(2): return False
        if not self.cmd(slot_number): return False  # CMD 1..4
        if not self.prm(0): return False  # PRM is 0 bij GOTO_POS
        if not self.sendcode(): return False
        return True
    
   

    def set_wavelength(self, wavelength, calib_file=None):
        if calib_file is None:
            calib_file = Path(__file__).resolve().parent / "wavelength_calib_Grating_300_500.txt"

        with open(calib_file, "r") as f:
            data = f.read()
        """
        Zet de golflengte door de motor naar de juiste positie te bewegen.
        
        Parameters:
            wavelength (float): gewenste golflengte in nm
            motor_controller: object van de Monocromator klasse (met positionAbs functie)
            calib_file (str): pad naar het calibratiebestand
        """
        # Lees calibratiebestand in: kolom 0 = golflengte, kolom 2 = motorpositie
        data = np.loadtxt(calib_file)
        wavelengths = data[:,0]
        positions = data[:,2]
    
        # Interpolatie: Cubic spline
        spline = CubicSpline(wavelengths, positions, extrapolate=True)
            
        # Bereken gewenste motorpositie
        target_pos = int(spline(wavelength))
    
        print(f"Setting wavelength to {wavelength} nm -> motor position {target_pos}")
        
        # Beweeg motor
        if not self.positionAbs(target_pos):
            print("Error: motor movement failed")
            return False
    

        if wavelength >= 1000:
            slot = 4
        if wavelength >= 645:
            slot = 3
        if wavelength >= 345:
            slot = 2
        else:
            slot = 1


        if not self.filterPos("filter", slot_number=slot):
            print(f"Error: filter slot {slot} switch failed")
            return False

        print(f"Wavelength set to {wavelength} nm with filter slot {slot}")
        return True
    
    


def list_monocromators():
    monocromators = []
    ports = list_ports.comports()
    for port in ports:
        monocromator = Monocromator(port.name)
        try:
            monocromator.open()
            if monocromator.sync() == True:
                monocromators.append(monocromator)
            monocromator.close()
        except:
            pass


    return monocromators

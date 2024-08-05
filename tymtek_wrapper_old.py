# this is an abstract class that interfaces with the TymTek API via the pyi interface
# and tracks/keeps the state of the TymTek devices and their capabilities for easy use

import argparse
import logging
import logging.config
import os
from pathlib import Path
import platform
import sys
import time
import traceback

logging.basicConfig(
level=logging.INFO,
format="%(asctime)s - %(name)s [%(levelname)s] %(message)s",
handlers=[logging.StreamHandler(sys.stdout),]
)

logger = logging.getLogger("Main")
logger.info("Python v%d.%d.%d (%s) on the %s platform" %(sys.version_info.major,
                                            sys.version_info.minor,
                                            sys.version_info.micro,
                                            platform.architecture()[0],
                                            platform.system()))

class TMYLogFileHandler(logging.FileHandler):
    """Handle relative path to absolute path"""
    def __init__(self, fileName, mode):
        super(TMYLogFileHandler, self).__init__(os.path.join(root_path, fileName), mode)

root_path = Path(__file__).absolute().parent
prefix = "TLKCore/lib/"
lib_path = os.path.join(root_path, prefix)
if os.path.exists(lib_path):
    sys.path.insert(0, os.path.abspath(lib_path))
    logging.info("Importing from path: %s" %lib_path)
else:
    print("Importing error: %s does not exist" %lib_path)
    exit(1)


from tlkcore.TLKCoreService import TLKCoreService
from tlkcore.TMYBeamConfig import TMYBeamConfig
from tlkcore.TMYPublic import (
    DevInterface,
    RetCode,
    RFMode,
    UDState,
    UDMState,
    BeamType,
    UD_REF          
)
logging.info("Successfully Imported TLKCoreServices")


class TMY_service():
    '''This is an abstract class that interfaces with the TymTek API'''
    def __init__(self, path='./TLKCore/lib', serial_numbers=None):
        '''if no arguments are given, the service will scan for all devices
        else, the service will scan for the given devices, initialize them, and create a device object for each device
        and return a list of device objects in the order of the given serial numbers'''
        self.logger = logging.getLogger("Main")
        self.logger.info("TMY_service.__init__()")
        self.devices = []

        # create a TLKCoreService object with the current directory as the path
        self.logger.info(f"Creating TLKCoreService object with path: {path}")
        self.service = TLKCoreService(path)

        # scan, init, and create devices
        interface = DevInterface.ALL #DevInterface.LAN | DevInterface.COMPORT
        self.logger.info("Searching devices via: %s" %interface)
        ret = self.service.scanDevices(interface=interface)
        scanlist = ret.RetData
        self.logger.info("Scanned device list: %s" %scanlist)
        
        if ret.RetCode is not RetCode.OK:
            if len(scanlist) == 0:
                self.logger.warning(ret.RetMsg)
                return False
        scan_dict = self.service.getScanInfo().RetData
            
        # if no *args as serial numbers are given, return the scan results
        if not serial_numbers:
            self.logger.info("No serial numbers given. Logging Scan Results Only")
            for ii, (sn, (addr, devtype)) in enumerate(list(scan_dict.items())):
                self.logger.info("Dev_%d: %s, %s, %d" %(ii, sn, addr, devtype))
            return None
        else: # create device objects for the given serial numbers in scan_dict or error
            for sn in serial_numbers:
                if sn not in scan_dict:
                    self.logger.error("Device %s not found in scan results" %sn)
                    return None
                else:
                    self.logger.info("Device %s found in scan results" %sn)
                    # create device objects for the given serial numbers
                    if self.service.initDev(sn).RetCode is not RetCode.OK:
                        self.logger.error("Init device %s failed" %sn)
                        return None
                    # else create a device object for the given serial number
                    address, devtype = scan_dict[sn][0], scan_dict[sn][1]:
                    # sort the devices by type and create the device objects
                    match devtype:
                        case 9: # BBoxOne5G
                            device = TMY_Device(self.service, sn, address, devtype)
                        case 15: # UDBox
                            pass
                        case _: # unknown device
                            self.logger.error("Unknown device type: %d" %devtype)

                    
                    if device is not None:
                        self.devices.append(device)
                        self.logger.info("Device %s created" %sn)
                    else:
                        self.logger.error("Device %s creation failed" %sn)
            return self.devices

class TMY_Device(TMY_service):
    '''This is an abstract class that interfaces with the TymTek API'''
    def __init__(self, serial_number:str, address:str, devtype:int):
        '''Initializes the TMY_Device object with the given service
        the type gives the devices capabilities and methods'''
        self.logger = logging.getLogger("Main")
        self.logger.info("TMY_Device.__init__()")
        self.serial_number = serial_number
        self.address = address
        self.devtype = devtype
        self.devtype_name = self.service.getDevTypeName(serial_number)
        

class UDBox(TMY_Device):
    '''This is a subclass of TMY_Device that interfaces with the BBoxOne5G device'''
    def __init__(self):
        '''Initializes the BB5G object with the given service
        the type gives the devices capabilities and methods'''
        self.logger = logging.getLogger("Main")
        self.logger.info("BB5G.__init__()")
        # setup the device specific parameters
        self.RF, self.LO, self.IF, self.BW = None, None, None, None
        self.freq_list = [self.RF, self.LO, self.IF, self.BW]
        self.state = self.service.getUDState(self.serial_number).RetData
        # break down state into individual states TODO*********************************
        self.freq_state = self.service.getUDFreq(self.serial_number)
        # turn off both channels
        self.service.setUDState(self.serial_number, 0, UDState.CH1)
        self.service.setUDState(self.serial_number, 0, UDState.CH2)

    def harmonic_check(self, freq_list):
        '''determine if the given frequency list contains any bad harmonics
        which would prevent the device from setting the given frequency list
        
        Parameters: freq_list = [RF, LO, IF, BW] all in KHz
        \n\texample: freq_list = [28_000_000, 25_548_000, 2_452_000, 50_000]
        
        Returns: True if successful, else False'''
        RF, LO, IF, BW = freq_list
        out = self.service.getHarmonic(self.serial_number, LO, RF, IF, BW).RetData
        return out
    
    def set_freq(self, freq_list):
        '''set the given frequency list to the device (if no bad harmonics are present)
        
        Parameters: freq_list = [RF, LO, IF, BW] all in KHz
        \n\texample: freq_list = [28_000_000, 25_548_000, 2_452_000, 50_000]

        Returns: True if successful, else False'''
        if not self.harmonic_check(freq_list):
            self.RF, self.LO, self.IF, self.BW = freq_list
            return self.service.setUDFreq(self.sn, self.RF, self.LO, self.IF, self.BW)
        else:
            self.logger.error("Bad Harmonics in the given frequency list")
        


# ---------------------------------------------------------- MAIN
if __name__ == "__main__":
    '''Main function to test the TMY_service class and TMY_Device class'''
    print("=== Welcome! Testing TMY_service and TMY_Device classes ===")
    TMY_service() # no serial numbers given, so only scan results are logged, no devices created

    # create a TMY_service object with the given serial numbers
    serials = ['UD-BD22470039-24','D2245E028-28','D2245E027-28']
    devices = TMY_service(serial_numbers=serials)



# this is an abstract class wapper that interfaces with the TymTek API via the pyi interface
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
from abc import ABC, abstractmethod
import numpy as np

logging.basicConfig(
level=logging.DEBUG, # change to INFO for runtime logging
format="%(asctime)s - %(name)s [%(levelname)s] %(message)s",
handlers=[logging.StreamHandler(sys.stdout),]
)

logger = logging.getLogger("Main")
logger.info("Python v%d.%d.%d (%s) on the %s platform" %(sys.version_info.major,
                                            sys.version_info.minor,
                                            sys.version_info.micro,
                                            platform.architecture()[0],
                                            platform.system()))
logger.debug("Current working directory: %s" %os.getcwd())

root_path = Path(__file__).absolute().parent
prefix = "TLKCore/lib/"
lib_path = os.path.join(root_path, prefix)
if os.path.exists(lib_path):
    sys.path.insert(0, os.path.abspath(lib_path))
    logging.info("Importing from path: %s" %lib_path)
else:
    print("Importing error: %s does not exist" %lib_path)
    exit(1)

class TMYLogFileHandler(logging.FileHandler):
    """Handle relative path to absolute path"""
    def __init__(self, fileName, mode):
        super(TMYLogFileHandler, self).__init__(os.path.join(root_path, fileName), mode)

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

# ----------------------------------------------------------------------- END OF IMPORTS

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
        # self.logger.info(f"Available methods in TLKCoreService: {dir(self.service)}")

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
            
        # if no serial numbers are given, return the scan results
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
                    devtype = scan_dict[sn][1]
                    # sort the devices by type and create the device objects
                    match devtype:
                        case 9: # BBoxOne5G
                            device = BBox5G(self, sn)
                            self.logger.info(f"BBoxOne5G device created: {sn}")
                        case 15: # UDBox
                            device = UDBox(self, sn)
                            self.logger.info(f"UDBox device created: {sn}")
                        case _: # unknown device
                            self.logger.error("Unknown device type: %d" %devtype)
                            device = None

                    if device is not None:
                        self.devices.append(device)
                        self.logger.info("Device %s created" %sn)
                    else:
                        self.logger.error("Device %s creation failed" %sn)

class TMY_Device(ABC):
    '''This is an abstract class that interfaces with the TymTek API'''
    def __init__(self, common_service:TMY_service, serial_number:str):
        '''Initializes the TMY_Device object with the given service
        the type gives the devices capabilities and methods'''
        self.logger = logging.getLogger("Main")
        self.service = common_service.service
        self.serial_number = serial_number        

        info = self.service.getScanInfo(self.serial_number).RetData
        self.logger.info("Device %s info: %s" %(self.serial_number, info))
        self.address, self.devtype = info
        self.devtype_name = self.service.getDevTypeName(serial_number)



    @abstractmethod
    def basic_setup(self, *args, **kwargs):
        '''setup the device to a known running state'''
        pass
        

class UDBox(TMY_Device):
    '''This is a subclass of TMY_Device that interfaces with the UDBox device'''
    def __init__(self,common_service:TMY_service, serial_number:str):
        '''Initializes the BB5G object with the given service
        the type gives the devices capabilities and methods'''
        super().__init__(common_service, serial_number)
        self.logger = logging.getLogger("Main")
        # setup the device specific parameters
        self.RF, self.LO, self.IF, self.BW = None, None, None, None
        self.freq_list:list[float] = [self.RF, self.LO, self.IF, self.BW]
        self.state:list[int] = self.service.getUDState(self.serial_number).RetData
        # break down state into individual states TODO*********************************
        self.freq_state = self.service.getUDFreq(self.serial_number)
        # turn off both channels
        # self.service.setUDState(self.serial_number, 0, UDState.CH1)
        # self.service.setUDState(self.serial_number, 0, UDState.CH2)
        self.logger.info("UDBox init complete: %s" %self.serial_number)

    def harmonic_check(self, freq_list:list|None = None):
        '''determine if the given frequency list contains any bad harmonics
        which would prevent the device from setting the given frequency list
        
        Parameters: freq_list = [RF, LO, IF, BW] all in KHz
        \n\texample: freq_list = [28_000_000, 25_548_000, 2_452_000, 50_000]
        
        Returns: True if successful, else False'''
        RF, LO, IF, BW = self.freq_list if freq_list is None else freq_list # use the current freq_list if none is given
        # if any of the frequencies are None, return False
        if None in [RF, LO, IF, BW]:
            self.logger.error("A frequency was not set: %s" %freq_list)
            return False
        out = self.service.getHarmonic(self.serial_number, LO, RF, IF, BW).RetData
        return out
    
    def set_freq(self, freq_list:list[float]):
        '''set the given frequency list to the device (if no bad harmonics are present)
        
        Parameters: freq_list = [RF, LO, IF, BW] all in KHz
        \n\texample: freq_list = [28_000_000, 25_548_000, 2_452_000, 50_000]

        Returns: True if successful, else False'''
        if not self.harmonic_check(freq_list):
            self.RF, self.LO, self.IF, self.BW = freq_list
            # return True if successful, else False
            return self.service.setUDFreq(self.serial_number, self.RF, self.LO, self.IF, self.BW).RetCode is RetCode.OK
        else:
            self.logger.error("Bad Harmonics in the given frequency list")
    
    def set_channel_state(self, channel:int, state:int):
        '''set the given channel to the given state (0=off, 1=on)
        
        Parameters: channel = 1 or 2, state = 0 or 1'''
        if channel not in [1,2]:
            self.logger.error("Invalid channel: %d" %channel)
            return False
        if state not in [0,1]:
            self.logger.error("Invalid state: %d" %state)
            return False
        # return True if successful, else False
        out = self.service.setUDState(self.serial_number, state, channel)
        # set the new state if successful
        if out.RetCode is RetCode.OK:
            self.state = self.service.getUDState(self.serial_number).RetData
            return True
        else:
            return False
    
    def basic_setup(self, freq_list:list[float]) -> bool:
        '''setup the UDBOX to a known running state
        Parameters: freq_list = [RF, LO, IF, BW] all in KHz
        \n\texample: freq_list = [28_000_000, 25_548_000, 2_452_000, 50_000]
        
        Returns: True if successful, else False'''
        return self.set_freq(freq_list)
    
    def disable_channels(self):
        '''turn off both channels'''
        state:bool = True
        state &= self.set_channel_state(1, 0)
        state &= self.set_channel_state(2, 0)
        self.logger.info("Both Channels Disabled: %s" %state)
        self.state = self.service.getUDState(self.serial_number).RetData
        return state

    
class BBox5G(TMY_Device): # BBoxOne5G with AAKit
    '''This is a subclass of TMY_Device that interfaces with the BBoxOne5G device'''
    def __init__(self,common_service:TMY_service, serial_number:str):
        '''Initializes the BB5G object with the given service
        the type gives the devices capabilities and methods'''
        super().__init__(common_service, serial_number)
        self.logger = logging.getLogger("Main")
        self.setup_complete = False
        # setup the device specific parameters
        self.target_freq:float = None # target frequency in in GHz (ex. 28.0)
        self.mode:RFMode = None # RFMode.TX or RFMode.RX
        self.AAKit:str = None # AAKit version
        self.calibration_version:str = None # calibration version
        self.num_boards:int = self.service.getBoardCount(self.serial_number).RetData
        self.logger.debug("Number of boards: %d" %self.num_boards)
        self.freq_list = self.service.getFrequencyList(self.serial_number).RetData
        self.beam_type:BeamType = None
        self.phi:float|None = None; self.theta:float|None = None; self.beam_gain:float|None = None
        self.beam = {'beam_gain': self.beam_gain, 'theta': self.theta, 'phi': self.phi}

        if len(self.freq_list) == 0 or self.freq_list is None:
            self.logger.error(f"Frequency list not found when setting up BB5G (serial): {self.serial_number}")
            self.logger.error("Check the \'files\' folder for available frequency configurations")
        else:
            self.logger.info(f"Frequency list found: {self.freq_list}")
        logger.info("BBox %s board temperatures: %s" %(self.serial_number, 
                                                       self.service.getTemperatureADC(self.serial_number).RetData))
        logger.info("BBox5G init complete: %s" %self.serial_number)

    def update_beam(self):
        '''update the beam dictionary with the current beam values'''
        self.beam = {'beam_gain': self.beam_gain, 'theta': self.theta, 'phi': self.phi}
        return self.beam
    
    def set_freq(self, RF:float):
        '''set the given frequency to the device
        
        Parameters: RF = target frequency in GHz (ex. 28.0)
        
        Returns: True if successful, else False'''

        if RF not in self.freq_list:
            self.logger.error("Frequency was not found in the frequency list: %s" %self.freq_list)
            self.logger.error("Check the \'files\' folder for available frequency configurations")
            return False
        # return True if successful, else False
        out = self.service.setOperatingFreq(self.serial_number, RF)
        self.target_freq = RF
        self.calibration_version = self.service.queryCaliTableVer(self.serial_number).RetData
        self.logger.debug("Target frequency: %s" %self.target_freq)
        self.logger.debug("Calibration version: %s" %self.calibration_version)
        return out.RetCode is RetCode.OK
    
    def set_AAKit(self, AAKit_name:str):
        '''set the AAKit version to the device. These are the antenna attached to the device.
        
        Parameters: AAKit_name = the name of the AAKit
        example: 'TMYTEK_28ONE_4x4_C2245E029-28'

        Returns: True if successful, else False
        '''
        # get the list of available AAKits
        aalist = self.service.getAAKitList(self.serial_number).RetData
        if AAKit_name not in aalist:
            self.logger.error("AAKit not found in the list: %s" %aalist)
            return False
        # return True if successful, else False
        return self.service.selectAAKit(self.serial_number, AAKit_name).RetCode is RetCode.OK
    
    def get_AAKit_list(self):
        '''get the list of available AAKits'''
        return self.service.getAAKitList(self.serial_number).RetData 
    
    def set_TXRX(self, mode:RFMode):
        '''set the device to the given mode (RFMode.TX or RFMode.RX)
        
        Parameters: mode = RFMode.TX or RFMode.RX
        
        Returns: True if successful, else False'''
        if mode in [RFMode.TX, RFMode.RX]:
            out = self.service.setRFMode(self.serial_number, mode).RetCode is RetCode.OK # return True if successful, else False
            if out:
                self.mode = mode
                self.logger.info(f"Set BBoxOne5G {self.serial_number} to mode: {mode}")
                # get and set the gains for the given mode
                self.dynamic_range = self.service.getDR(self.serial_number, mode).RetData
                self.logger.debug("Dynamic Range: %s" %self.dynamic_range)
                self.gain_min,self.gain_max = self.dynamic_range
                cg = self.service.getCOMDR(self.serial_number).RetData
                self.logger.debug("Common Dynamic Range: %s" %cg)
                self.common_gain:list[float] = cg[mode.value] #Common Dynamic Range, for the given mode, for each board
                self.logger.info(f"Common Gain [{self.mode.name}]: {self.common_gain}")
                ele = self.service.getELEDR(self.serial_number).RetData
                self.logger.debug("Element Dynamic Range: %s" %ele)
                self.ele_dir_limit = ele[mode.value] # Element(board)-wise Dynamic Range, for each board
                self.logger.info(f"Element Dynamic Range [{self.mode.name}]: {self.ele_dir_limit}")
                return True
            else:
                self.logger.error("Failed to set mode: %d" %mode)
                return False
        else:
            self.logger.error("Invalid mode: %d" %mode)
            return False
        
    def basic_setup(self, target_freq:float, mode:RFMode, AAKit_name:str):
        '''setup the device to a known running state'''
        self.setup_complete:bool = True # any failure will set this to False
        self.setup_complete &= self.set_freq(target_freq)
        self.logger.debug("SETUP: Frequency set: %s" %self.setup_complete)
        self.setup_complete &= self.set_AAKit(AAKit_name)
        self.logger.debug("SETUP: AAKit set: %s" %self.setup_complete)
        self.setup_complete &= self.set_TXRX(mode)
        self.logger.debug("SETUP: Mode set: %s" %self.setup_complete)
                                                                                  
        return self.setup_complete

    def boresight(self):
        '''set the device to the "boresight", 
        0 degrees theta, 0 degrees phi'''
        if self.setup_complete:
            ret = self.service.setBeamAngle(self.serial_number, self.gain_max,0,0).RetCode is RetCode.OK
            if ret:
                self.logger.debug(f"{self.serial_number} Boresight: {self.gain_max}dB, theta:0, phi:0")
                self.beam_type = BeamType.BEAM
                self.phi = 0; self.theta = 0; self.beam_gain = self.gain_max
                self.update_beam()
                return True
        else:
            self.logger.error("Setup not complete")
            return False
    
    def set_beam_angle(self, gain:float, theta:float, phi:float):
        '''set the device to the given beam angle
        
        Parameters: gain = gain in dB, theta = theta angle in degrees, phi = phi angle in degrees
        \ntheta is a polar angle from down the Z (or bore) axis of the beamformer
        \nphi is a azimuth angle on the xy-plane
        
        Returns: True if successful, else False'''
        gain_min,gain_max = self.dynamic_range
        if gain < gain_min or gain > gain_max:
            self.logger.error("Gain out of range: %s" %gain)
            return False
        theta_min,theta_max = 0, 45 # these are the limits for the BBoxOne5G
        if theta < theta_min or theta > theta_max:
            self.logger.error("Theta out of range: %s" %theta)
            return False
        phi_min,phi_max = 0, 359 # these are the limits for the BBoxOne5G
        if phi < phi_min or phi > phi_max:
            self.logger.error("Phi out of range: %s" %phi)
            return False
        if self.setup_complete:
            ret = self.service.setBeamAngle(self.serial_number, gain, theta, phi).RetCode is RetCode.OK
            if ret:
                self.logger.debug(f"{self.serial_number} Beam Angle: {gain}dB, theta:{theta}, phi:{phi}")
                self.beam_type = BeamType.BEAM
                self.phi = phi; self.theta = theta; self.beam_gain = gain
                self.update_beam()
                return True
            else:
                self.logger.error(f"Failed to set {self.serial_number} Beam Angle: {gain}dB, theta:{theta}, phi:{phi}")
                return False
        else:
            self.logger.error("Setup not complete")
            return False
        
    def check_gain(self, gain:float):
        '''check if the given gain is within the dynamic range'''
        gain_min,gain_max = self.dynamic_range
        if gain < gain_min or gain > gain_max:
            self.logger.error("Gain out of range: %s" %gain)
            return False
        return True
    def check_theta(self, theta:float):
        '''check if the given theta is within the range'''
        theta_min,theta_max = 0, 45.0
        if theta < theta_min or theta > theta_max:
            self.logger.error("Theta out of range: %s" %theta)
            return False
        return True
    def check_phi(self, phi:float):
        '''check if the given phi is within the range'''
        phi_min,phi_max = 0, 359.9
        if phi < phi_min or phi > phi_max:
            self.logger.error("Phi out of range: %s" %phi)
            return False
        return True
    
        
    def scan_raster_generator(self, theta_range:list[float] = [1.0,45.0], 
                                    phi_range:list[float] = [0,359.9], 
                                    theta_step:float = 1.0,
                                    phi_step:float = 1.0,
                                    gain:float|None = None):
        '''setup a scan generator for the device, this will allow the device to scan the given ranges
        yields the itteration number if successful, else None if error, setup not complete, or finished
        the gain given or set before the scan starts, if not set or given, it will be scanned with the max gain
        \ntheta is a polar angle from down the Z (or bore) axis of the beamformer
        \nphi is a azimuth angle on the xy-plane'''
        if self.setup_complete is False:
            self.logger.error("Setup not complete")
            return None

        # handle the beam gain
        if gain is None: # no gain is given as an argument
            gain = self.beam_gain
            if gain is None: # no gain was set before
                gain = self.gain_max # default to the max gain
                self.logger.warning("No gain set, scan generator defaulting to max gain: %s" %gain)
        else: # a gain is given as an argument
            if gain < self.gain_min or gain > self.gain_max:
                self.logger.error("Gain specified was out of range: %s" %gain)
                self.logger.error("Setting generator gain to max gain: %s" %self.gain_max)
                gain = self.gain_max

        # handle the theta and phi ranges
        if not self.check_theta(theta_range[0]) or not self.check_theta(theta_range[1]):
            self.logger.error("Theta range out of bounds: %s" %theta_range)
            return None
        if not self.check_phi(phi_range[0]) or not self.check_phi(phi_range[1]):
            self.logger.error("Phi range out of bounds: %s" %phi_range)
            return None

        self.logger.info("Setting up scan generator")
        self.logger.info(f"Theta Range: {theta_range}, Phi Range: {phi_range}")
        self.logger.info(f"Theta Step: {theta_step}, Phi Step: {phi_step}")
        self.beam_type = BeamType.BEAM
        # generate the beams for the given ranges as a list of tuples
        beams = [(theta,phi) for theta in np.arange(theta_range[0], theta_range[1], theta_step)
                            for phi in np.arange(phi_range[0], phi_range[1], phi_step)]
        # add a boresight beam to the beginning of the list
        beams.insert(0, (0,0))
        len_beams = len(beams)
        self.logger.info(f"Generated Beams: {len_beams}")
        scan_complete = False
        # GENERATOR LOOP ---------------------------------------------------
        while not scan_complete:
            for ii, (theta,phi) in enumerate(beams):
                self.logger.debug(f"Setting Beam: {ii+1} of {len_beams}")
                if self.set_beam_angle(self.beam_gain, theta, phi): # gain, theta, phi (gain is set be)
                    self.logger.debug(f"Beam {ii+1} set to: {self.beam}")
                    yield ii
                else:
                    self.logger.error(f"Failed to set Beam {ii+1} to: {theta}, {phi}")
                    yield None
            scan_complete = True
            self.logger.info("Scan generator setup complete")
            yield None


# ---------------------------------------------------------- MAIN
if __name__ == "__main__":
    '''Main function to test the TMY_service class and TMY_Device class'''
    print("=== Welcome! Testing TMY_service and TMY_Device classes ===")
    # TMY_service() # if no serial numbers given, so only scan results are logged, no devices created

    # create a TMY_service object with the given serial numbers as a list of devices
    serials = ['UD-BD22470039-24','D2245E028-28','D2245E027-28']
    aakits = [None, 'TMYTEK_28ONE_4x4_C2245E029-28', 'TMYTEK_28ONE_4x4_C2245E030-28'] # antenna kit for device

    logger.info("Looking for Devices with serial numbers: %s" %serials)
    udbox:UDBox; txbbox:BBox5G; rxbbox:BBox5G # typehinting for the devices
    service = TMY_service(serial_numbers=serials)
    # get the devices from the service
    udbox, txbbox, rxbbox = service.devices

    # setup the devices ----------------------------------------------
    # setup the UDBox device
    freq_list = [28_000_000, 25_548_000, 2_452_000, 50_000]
    if udbox.basic_setup(freq_list): logger.info("UDBox setup complete")
    else: logger.error("UDBox setup failed")

    # setup the BBoxOne5G devices
    if txbbox.basic_setup(28.0, RFMode.TX, aakits[1]): logger.info("TX BBoxOne5G setup complete")
    else: logger.error("TX BBoxOne5G setup failed")
    if rxbbox.basic_setup(28.0, RFMode.RX, aakits[2]): logger.info("RX BBoxOne5G setup complete")
    else: logger.error("RX BBoxOne5G setup failed")

    # set a test beam angle
    logger.info("Setting BBoxOne5G devices to test beam angle")
    if txbbox.set_beam_angle(txbbox.gain_max, 10, 270): logger.info(f"{txbbox.serial_number} set to {txbbox.beam}") # gain, theta, phi
    if rxbbox.set_beam_angle(rxbbox.gain_max, 30, 180): logger.info(f"{rxbbox.serial_number} set to {rxbbox.beam}")

    # test beam angle with float input values for theta and phi
    if txbbox.set_beam_angle(txbbox.gain_max, 10.5, 270.5): logger.info(f"{txbbox.serial_number} set to {txbbox.beam}")
    if rxbbox.set_beam_angle(rxbbox.gain_max, 30.5, 180.5): logger.info(f"{rxbbox.serial_number} set to {rxbbox.beam}")

    # make both devices boresight
    logger.info("Setting BBoxOne5G devices to boresight")
    txbbox.boresight()
    logger.info(f"{txbbox.serial_number} set to {txbbox.beam}")
    rxbbox.boresight()
    logger.info(f"{rxbbox.serial_number} set to {rxbbox.beam}")

    # test the scan raster generator
    start_time = time.time()
    logger.info("Testing the scan raster generator")
    for ret in txbbox.scan_raster_generator([1,45], [0.0,359], 5.0, 15.0):
        if ret is False: break
        time.sleep(0.01)
    logger.info("Scan raster generator test complete")
    logger.info("Elapsed time: %s" %(time.time()-start_time))


    # disable the UDBox channels
    logger.info("Disabling UDBox channels")
    udbox.disable_channels()

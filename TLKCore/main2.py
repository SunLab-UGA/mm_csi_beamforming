import argparse
import logging
import logging.config
import os
from pathlib import Path
import platform
import sys
import time
import traceback

service = None
root_path = Path(__file__).absolute().parent

# Please setup path of tlkcore libraries to environment variables,
# here is a example to search from 'lib/' or '.'
prefix = "lib/"
lib_path = os.path.join(root_path, prefix)
if os.path.exists(lib_path):
    sys.path.insert(0, os.path.abspath(lib_path))
else:
    print("Importing from source code")

try:
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
except Exception as e:
    print("[Main] Import path has soomething wrong")
    print(sys.path)
    traceback.print_exc()
    os._exit(-1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        # logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug.log')),
    ]
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

def startService(root:str=".", direct_connect_info:list=None, dfu_image:str=""):
    """ALL return type from TLKCoreService always be RetType,
    and it include: RetCode, RetMsg, RetData,
    you could fetch service.func().RetData
    or just print string result directly if you make sure it always OK"""
    # You can assign a new root directory into TLKCoreService() to change files and log directory
    if Path(root).exists() and Path(root).absolute() != Path(root_path):
        service = TLKCoreService(root)
        logger.info("TLKCoreService loaded with root: %s" %root)
        logger.info("Current working directory: %s" %os.getcwd())
    else:
        service = TLKCoreService()
        logger.info("TLKCoreService loaded with default root: %s" %root_path)
        logger.info("Current working directory: %s" %os.getcwd())
    logger.info("TLKCoreService v%s %s" %(service.queryTLKCoreVer(), "is running" if service.running else "can not run"))

    if not service.running:
        return False
    else:
        return service

def scan_devices(service):
    interface = DevInterface.ALL #DevInterface.LAN | DevInterface.COMPORT
    logger.info("Searching devices via: %s" %interface)
    ret = service.scanDevices(interface=interface)

    scanlist = ret.RetData
    logger.info("Scanned device list: %s" %scanlist)
    if ret.RetCode is not RetCode.OK:
        if len(scanlist) == 0:
            logger.warning(ret.RetMsg)
            return False
        else:
            input(" === There is some errors while scanning, do you want to continue? ===")

    scan_dict = service.getScanInfo().RetData
    # You can also get the info for specific SN
    # scan_dict = service.getScanInfo(sn).RetData
    i = 0
    for sn, (addr, devtype) in list(scan_dict.items()):
        logger.info("Dev_%d: %s, %s, %d" %(i, sn, addr, devtype))
        

        # Init device, the first action for device before the operations
        if service.initDev(sn).RetCode is not RetCode.OK:
            logger.error("Init device %s failed" %sn)
            continue
        # testDevice(sn, service, dfu_image)
        logger.info("device type Name: %s" %service.getDevTypeName(sn))
        i+=1

    if i == 0:
        logger.warning("No device available")
        return False
    else:
        logger.info("Total %d devices found" %i)
        return scan_dict

# This doesn't seem to work...or is depreciated
# def deinit_devices(service, devices_sn:list):
#     for sn in devices_sn:
#         logger.info("DeInit device: %s" %service.deInitDev(sn).name)

def setup_UDBox(service, serial_number:str, freq_list:list):
    '''Setup the BBox with the given frequency list:
    [RF, LO, IF, BW] given in kHz
    ex. [28_000_000, 25_548_000, 2_452_000, 50_000]
    '''
    sn = serial_number # BBox serial number
    RF, LO, IF, BW = freq_list # unpack the freq list
    dev_name = service.getDevTypeName(sn)
    logger.info(f"Setting up Device: {dev_name}, sn: {sn}")
    # turn off the CH1 and CH2
    logger.info(service.setUDState(sn, 0, UDState.CH1)) # set CH1
    logger.info(service.setUDState(sn, 0, UDState.CH2)) # set CH2

    logger.info("PLO state: %r" %service.getUDState(sn, UDState.PLO_LOCK).RetData)
    logger.info("All state: %r" %service.getUDState(sn).RetData)
    logger.info("Get current freq: %s" %service.getUDFreq(sn))

    logger.info(service.setUDState(sn, UD_REF.INTERNAL, UDState.SOURCE_100M)) # set internal 100M

    logger.info("Harmonic/Freq Check: %r" %service.getHarmonic(sn, LO, RF, IF, BW).RetData)
    ret = service.setUDFreq(sn, LO, RF, IF, BW)
    logger.info("Freq config: %s" %ret)

    if ret.RetCode is not RetCode.OK: # freq config failed
        return False

    logger.info(service.setUDState(sn, 1, UDState.CH1))
    logger.info(service.setUDState(sn, 1, UDState.CH2))
    logger.info("Get current freq: %s" %service.getUDFreq(sn))
    logger.info("All state: %r" %service.getUDState(sn).RetData)
    return True

def setup_BBox(service, serial_number:str, mode:RFMode, freq_list:list):
    '''Setup the BBox'''
    sn = serial_number # BBox serial number
    target_freq = round(freq_list[0]/1e6, 1) # unpack freq (in kHz to GHz), round to 1 decimal
    logger.info(f"Setting up BBox: {sn} for mode: {mode}")
    logger.info(f"setting freq: {target_freq} GHz")
    logger.info("Set RF mode: %s" %service.setRFMode(sn, mode).name)
    freq_list = service.getFrequencyList(sn).RetData
    print(f'found freq config files for: {freq_list}')
    if target_freq not in freq_list:
        logger.error("Not support your target freq:%f in freq list!")
        return False
    
    ret = service.setOperatingFreq(sn, target_freq)
    if ret.RetCode is not RetCode.OK:
        logger.error("Set operating freq failed")
        return False
    else:
        logger.info("Get freq: %s" %service.getOperatingFreq(sn))
        logger.info("Cali ver: %s" %service.queryCaliTableVer(sn))

    # gain settings
    rng = service.getDR(sn, mode).RetData # get dynamic range
    logger.info("DR range: %s" %rng)
    gain_max = rng[1] # caution! no error checking
    gain_min = rng[0]

    # select AAKit (antenna array kit)
    aakitList = service.getAAKitList(sn).RetData
    # logger.info("AAKit list: %s" %aakitList)
    if len(aakitList) == 0:
        logger.warning("No AAKit file found, check \'files\' directory")
        return False
    if sn == 'D2245E027-28': 
        aakit = 'TMYTEK_28ONE_4x4_C2245E029-28'
    if sn == 'D2245E028-28':
        aakit = 'TMYTEK_28ONE_4x4_C2245E030-28'
    logger.info("Select AAKit: %s, return %s" %(aakit, service.selectAAKit(sn, aakit).name))
    
    board_count = service.getBoardCount(sn).RetData
    logger.info("Board count: %d" %board_count)
    com_dr = service.getCOMDR(sn).RetData # get common dynamic range
    logger.info("Common DR: %s" %com_dr)
    for board in range(1, board_count+1):
        common_gain_rng = com_dr[mode.value][board-1]
        common_gain_max = common_gain_rng[1]
        ele_dr_limit = service.getELEDR(sn).RetData[mode.value][board-1]
        logger.info("Board:%d common gain range: %s, and element gain limit: %s"
                        %(board, common_gain_rng, ele_dr_limit))
        
    # set bore sight beam (serial, gain, theta, phi)
    logger.info("SetBeamAngle-boresight: %s" %service.setBeamAngle(sn, gain_max, 0, 0))
    

    logger.info("BBox %s board temperatures: %s" %(sn, service.getTemperatureADC(sn).RetData))
    
    return True

def main():
    RF = 28_000_000 # kHz, output frequency
    LO = 25_548_000 # kHz, local oscillator frequency
    IF = 2_452_000 # kHz, intermediate frequency
    BW = 50_000 # kHz, bandwidth (50MHz)
    FREQ_LIST = [RF, LO, IF, BW]

    TX_GAIN = 0 # dB
    RX_GAIN = 0 # dB

    # known serials
    BBOX_serial = 'UD-BD22470039-24'
    UDBOX1_serial = 'D2245E027-28' # TX
    UDBOX2_serial = 'D2245E028-28' # RX
    devices_sn = [BBOX_serial, UDBOX1_serial, UDBOX2_serial]

    # start the service and return the scan results ---------------------------
    service = startService() # start the service
    devices = scan_devices(service) # scan the devices and init them

    # check if all 3 devices are connected ------------------------------------
    if len(devices) != 3:
        logger.error("Some devices are not connected, please check the connection and try again.")
        os._exit(-1)

    #  setup the Boxes ---------------------------------------------------------
    UD_status = setup_UDBox(service, BBOX_serial, FREQ_LIST) # setup the freq upconverter
    tx_mode = RFMode.TX
    rx_mode = RFMode.RX
    BB1_status = setup_BBox(service, UDBOX1_serial, tx_mode, FREQ_LIST) # setup the first BBox
    BB2_status = setup_BBox(service, UDBOX2_serial, rx_mode, FREQ_LIST) # setup the second BBox
    
    if not UD_status or not BB1_status or not BB2_status:
        logger.error("Setup failed, please check the setup and try again.")
        os._exit(-1)

    # system is ready to go ---------------------------------------------------
    logger.info("System is ready to go")

    input("Press Enter to disable UDBox channels 1 and 2 ...")
    logger.info(service.setUDState(BBOX_serial, 0, UDState.CH1)) # set CH1
    logger.info(service.setUDState(BBOX_serial, 0, UDState.CH2)) # set CH1

    # disable all channels ???
    for sn in devices_sn[1:]:
        logger.info("Disabling channels for: %s" %sn)
        for ch in range(1, 17): # 16 channels
            logger.info("Disabled channel %s: %s" % (ch, service.switchChannel(sn, ch, True)))

    logger.info("end")


if __name__ == '__main__':
    main()


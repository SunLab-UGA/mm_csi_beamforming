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

def wrapper(*args, **kwarg):
    """It's a wrapper function to help some API developers who can't call TLKCoreService class driectly,
    so developer must define return type if using LabVIEW/MATLAB"""
    global service
    if len(args) == 0:
        logger.error("Invalid parameter: please passing function name and parameters")
        raise Exception
    if service is None:
        service = TLKCoreService(log_path=os.path.join(root_path, 'logging_abs.conf'))
        logger.info("TLKCoreService v%s %s" %(service.queryTLKCoreVer(), "is running" if service.running else "can not run"))
        logger.info(sys.path)

    arg_list = list(args)
    func_name = arg_list.pop(0)
    logger.info("Calling dev_func: \'%s()\'with %r and %r" % (func_name, arg_list, kwarg))
    if not hasattr(service, func_name):
        service = None
        msg = "TLKCoreService not support function name: %s()" %func_name
        logger.error(msg)
        raise Exception(msg)

    for i in range(1, len(arg_list)): # skip first for sn
        p = arg_list[i]
        if type(p) is str and p.__contains__('.'):
            try:
                # Parsing and update to enum type
                logger.debug("Parsing: %s" %p)
                str_list = p.split('.')
                type_str = str_list[0]
                value_str = str_list[1]
                f = globals()[type_str]
                v = getattr(f, value_str)
                arg_list[i] = v
            except Exception:
                service = None
                msg = "TLKCoreService scan result parsing failed"
                logger.error(msg)
                raise Exception(msg)

    # Relfect and execute function in TLKCoreService
    ret = getattr(service, func_name)(*tuple(arg_list))
    if not hasattr(ret, "RetCode"):
        return ret
    if ret.RetCode is not RetCode.OK:
        service = None
        msg = "%s() returned: [%s] %s" %(func_name, ret.RetCode, ret.RetMsg)
        logger.error(msg)
        raise Exception(msg)

    if ret.RetData is None:
        logger.info("%s() returned: %s" %(func_name, ret.RetCode))
        return str(ret.RetCode)
    else:
        logger.info("%s() returned: %s" %(func_name, ret.RetData))
        return ret.RetData

def startService(root:str=".", direct_connect_info:list=None, dfu_image:str=""):
    """ALL return type from TLKCoreService always be RetType,
    and it include: RetCode, RetMsg, RetData,
    you could fetch service.func().RetData
    or just print string result directly if you make sure it always OK"""
    # You can assign a new root directory into TLKCoreService() to change files and log directory
    if Path(root).exists() and Path(root).absolute() != Path(root_path):
        service = TLKCoreService(root)
    else:
        service = TLKCoreService()
    logger.info("TLKCoreService v%s %s" %(service.queryTLKCoreVer(), "is running" if service.running else "can not run"))

    if not service.running:
        return False

    if isinstance(direct_connect_info, list) and len(direct_connect_info) == 3:
        # For some developers just connect device and the address always constant (static IP or somthing),
        # So we provide a extend init function to connect device driectly without scanning,
        # the parameter address and devtype could fetch by previous results of scanning.
        # The following is simple example, please modify it
        direct_connect_info[2] = int(direct_connect_info[2]) # convert to dev_type:int
        # Parameter: SN, Address, Devtype
        ret = service.initDev(*tuple(direct_connect_info))
        if ret.RetCode is RetCode.OK:
            testDevice(direct_connect_info[0], service, dfu_image)
    else:
        # Please select or combine your interface or not pass any parameters: service.scanDevices()
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
                continue
            testDevice(sn, service, dfu_image)
            i+=1
    return True

def testDevice(sn, service, dfu_image:str=""):
    """ A simple query operations to device """
    logger.info("SN: %s" %service.querySN(sn))
    logger.info("FW ver: %s" %service.queryFWVer(sn))
    logger.info("HW ver: %s" %service.queryHWVer(sn))

    dev_name = service.getDevTypeName(sn)
    # print(dev_name)

    # Process device testing, runs a device test function likes testPD, testBBox, testUD ...etc
    # 1. parameters
    kw = {}
    kw['sn'] = sn
    kw['service'] = service

    # 2. test function name
    if len(dfu_image) > 0 and 'BBo' in dev_name:
        # DFU test case for BBox series
        kw['dfu_image'] = dfu_image
        f = globals()["startBFDFU"]
    else:
        if 'BBoard' in dev_name:
            dev_name = "BBoard"
        elif 'BBox' in dev_name:
            dev_name = "BBox"
        f = globals()["test"+dev_name]

    # Start testing
    f(**kw)

    service.DeInitDev(sn)

""" ----------------- Test examples for TMY devices ----------------- """

__caliConfig = {
    "0.1GHz": {
            "lowPower": -35,
            "lowVolt": 34.68,
            "highPower": -5,
            "highVolt": 901.68
        },
    "0.3GHz": {
            "lowPower": -36,
            "lowVolt": 34.68,
            "highPower": -5,
            "highVolt": 901.68
        },
    "0.5GHz": {
            "lowPower": -36,
            "lowVolt": 109.98,
            "highPower": -5,
            "highVolt": 984.18
        },
    "1GHz": {
            "lowPower": -36,
            "lowVolt": 109.98,
            "highPower": -5,
            "highVolt": 984.18
        },
    "10GHz": {
            "lowPower": -36,
            "lowVolt": 57.6,
            "highPower": -5,
            "highVolt": 950.4
        },
    "20GHz": {
            "lowPower": -36,
            "lowVolt": 40.46,
            "highPower": -5,
            "highVolt": 936.36
        },
    "30GHz": {
            "lowPower": -36,
            "lowVolt": 83.81,
            "highPower": -5,
            "highVolt": 979.71
        },
    "40GHz": {
            "lowPower": -30,
            "lowVolt": 20.65,
            "highPower": -5,
            "highVolt": 787.65
        },
    "43GHz": {
            "lowPower": -28,
            "lowVolt": 20.65,
            "highPower": -5,
            "highVolt": 787.65
        }
}

def testPD(sn, service):
    for freq, config in __caliConfig.items():
        logger.info("Process cali %s: %s" %(freq, service.setCaliConfig(sn, {freq: config})))

    target_freq = 28
    for _ in range(10):
        logger.info("Fetch voltage: %s" %service.getVoltageValue(sn, target_freq))
        logger.info("        power: %s" %service.getPowerValue(sn, target_freq))
    logger.info("Reboot test: %s" %service.reboot(sn))

    while(True):
        try:
            logger.info("power: %s" %(service.getPowerValue(sn, target_freq)))
            time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            print("Detected Ctrl+C")
            break

def testUDBox(sn, service):
    logger.info("PLO state: %r" %service.getUDState(sn, UDState.PLO_LOCK).RetData)
    logger.info("All state: %r" %service.getUDState(sn).RetData)
    logger.info(service.setUDState(sn, 0, UDState.CH1))
    input("Wait for ch1 off")
    # logger.info(service.setUDState(sn, 1, UDState.SOURCE_100M))
    logger.info(service.setUDState(sn, 1, UDState.CH1))
    logger.info(service.setUDState(sn, 1, UDState.CH2))
    logger.info(service.setUDState(sn, 1, UDState.OUT_10M))
    logger.info(service.setUDState(sn, 1, UDState.OUT_100M))
    logger.info(service.setUDState(sn, 1, UDState.PWR_5V))
    logger.info(service.setUDState(sn, 1, UDState.PWR_9V))

    input("Wait")
    # Switch 100M reference source to external: 1
    logger.info(service.setUDState(sn, UD_REF.EXTERNAL, UDState.SOURCE_100M))
    input("Wait to switch")
    logger.info("PLO state: %r" %service.getUDState(sn, UDState.PLO_LOCK).RetData)

    # Switch 100M reference source to internal: 0
    logger.info(service.setUDState(sn, UD_REF.INTERNAL, UDState.SOURCE_100M))
    input("Wait to switch")
    logger.info("PLO state: %r" %service.getUDState(sn, UDState.PLO_LOCK).RetData)

    logger.info("Get current freq: %s" %service.getUDFreq(sn))
    # Passing: LO, RF, IF, Bandwidth with kHz
    LO = 24e6
    RF = 28e6
    IF = 4e6
    BW = 1e5
    # A check function
    logger.info("Check harmonic: %r" %service.getHarmonic(sn, LO, RF, IF, BW).RetData)
    # SetUDFreq also includes check function
    ret = service.setUDFreq(sn, LO, RF, IF, BW)
    logger.info("Freq config: %s" %ret)

def testUDM(sn, service):
    # Just passing parameter via another way
    param = {"sn": sn}
    param['item'] = UDMState.REF_LOCK | UDMState.SYSTEM | UDMState.PLO_LOCK
    ret = service.getUDState(**param)
    if ret.RetCode is not RetCode.OK:
        return logger.error("Error to get UDM state: %s" %ret)
    logger.info("UDM state: %s" %ret)
    lock = ret.RetData[UDMState.REF_LOCK.name]

    # Passing parameter with normal way
    logger.info("UDM freq capability range: %s" %service.getUDFreqLimit(sn))
    logger.info("UDM available freq range : %s" %service.getUDFreqRange(sn))

    # service.reboot(sn)
    # input("Wait for rebooting...Please press ENTER to continue")

    logger.info("UDM current freq: %s" %service.getUDFreq(sn))
    service.setUDFreq(sn, 7e6, 10e6, 3e6, 100000)
    logger.info("UDM current freq: %s" %service.getUDFreq(sn))

    # We use reference config to try reference source switching
    source = service.getRefConfig(sn).RetData['source']
    logger.info("UDM current ref source setting: %s, and real reference status is: %s" %(source, lock))

    if source is UD_REF.INTERNAL:
        # INTERNAL -> EXTERNAL
        source = UD_REF.EXTERNAL
        # Get external reference source supported list
        supported = service.getRefFrequencyList(sn, source).RetData
        logger.info("Supported external reference clock(kHz): %s" %supported)
        # Try to change reference source to external: 10M
        ret = service.setRefSource(sn, source, supported[0])
        logger.info("Change UDM ref source to %s -> %s with freq: %d" %(source, ret, supported[0]))
        input("Waiting for external reference clock input")
    elif source is UD_REF.EXTERNAL:
        # EXTERNAL -> INTERNAL
        source = UD_REF.INTERNAL
        ret = service.setRefSource(sn, source)
        logger.info("Change UDM ref source to %s -> %s" %(source, ret))

        # Get internal reference source supported list
        supported = service.getRefFrequencyList(sn, source).RetData
        logger.info("Supported internal output reference clock(kHz): %s" %supported)

        # Output 10MHz ref clock
        enable = not service.getOutputReference(sn).RetData
        output_freq = supported[0]
        logger.info("%s UDM ref output(%dkHz): %s"
                    %("Enable" if enable else "Disable", output_freq, service.setOutputReference(sn, enable, output_freq)))
        logger.info("Get UDM ref ouput: %s" %service.getOutputReference(sn))

        input("Typing ENTER to disable output")
        enable = not enable
        logger.info("%s UDM ref output: %s"
                    %("Enable" if enable else "Disable", service.setOutputReference(sn, enable, output_freq)))
        logger.info("Get UDM ref ouput: %s" %service.getOutputReference(sn))

    source = service.getRefConfig(sn).RetData
    lock = service.getUDState(sn, UDMState.REF_LOCK).RetData[UDMState.REF_LOCK.name]
    logger.info("UDM current ref source setting: %s, and real reference status is: %s" %(source, lock))

def testBBox(sn, service):
    logger.info("MAC: %s" %service.queryMAC(sn))
    logger.info("Static IP: %s" %service.queryStaticIP(sn))
    # Sample to passing parameter with dict
    # a = {}
    # a["ip"] = '192.168.100.122'
    # a["sn"] = sn
    # logger.info("Static IP: %s" %service.setStaticIP(**a))
    # logger.info("Export dev log: %s" %service.exportDevLog(sn))

    mode = RFMode.TX
    logger.info("Set RF mode: %s" %service.setRFMode(sn, mode).name)
    logger.info("Get RF mode: %s" %service.getRFMode(sn))

    freq_list = service.getFrequencyList(sn).RetData
    if len(freq_list) == 0:
        logger.error("CAN NOT find your calibration files in \'files\' -> exit")
        return
    logger.info("Available frequency list: %s" %freq_list)

    # Please edit your target freq
    target_freq = 28.0
    if target_freq not in freq_list:
        logger.error("Not support your target freq:%f in freq list!")
        return

    ret = service.setOperatingFreq(sn, target_freq)
    if ret.RetCode is not RetCode.OK:
        logger.error("Set freq: %s" %ret)
        ans = input("Do you want to continue to processing? (Y/N)")
        if ans.upper() == 'N':
            return
    logger.info("Set freq: %s" %ret.RetCode)
    logger.info("Get freq: %s" %service.getOperatingFreq(sn))
    logger.info("Cali ver: %s" %service.queryCaliTableVer(sn))

    # Gain setting for BBoxOne/Lite
    rng = service.getDR(sn, mode).RetData
    logger.info("DR range: %s" %rng)

    # Set/save AAKit
    # custAAKitName = 'MyAAKIT'
    # logger.info("Set AAKit: %s" %service.setAAKitInfo(sn,
    #                                                   custAAKitName,
    #                                                   ["0","0"],
    #                                                   ["-100","100"],
    #                                                   ["0","0"],
    #                                                   ["0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0"],
    #                                                   ["0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0"]))
    # logger.info("Save AAKit: %s" %service.saveAAKitFile(sn, custAAKitName))
    # logger.info("Get AAKitList: %s" %service.getAAKitList(sn))
    # logger.info("Get AAKitInfo: %s" %service.getAAKitInfo(sn, custAAKitName))

    # Select AAKit, please call getAAKitList() to fetch all AAKit list in files/
    aakit_selected = False
    aakitList = service.getAAKitList(sn).RetData
    for aakit in aakitList:
        if '4x4' in aakit:
            logger.info("Select AAKit: %s, return %s" %(aakit, service.selectAAKit(sn, aakit).name))
            aakit_selected = True
            break
    if not aakit_selected:
        logger.warning("PhiA mode")

    # get basic operating infomations
    gain_max = rng[1]
    # Set IC channel gain, we use board 1 (its index in com_dr is 0) as example
    board_count = service.getBoardCount(sn).RetData
    board = 1
    logger.info("Selected board:%d/%d" %(board, board_count))

    com_dr = service.getCOMDR(sn).RetData
    common_gain_rng = com_dr[mode.value][board-1]
    # Here we takes the maximum common gain as example
    common_gain_max = common_gain_rng[1]
    ele_dr_limit = service.getELEDR(sn).RetData[mode.value][board-1]
    logger.info("Board:%d common gain range: %s, and element gain limit: %s"
                    %(board, common_gain_rng, ele_dr_limit))

    # Test example options, your can decide what to test
    testChannels = True
    testBeam = False
    testFBS = False

    if testChannels:
        """Individual gain/phase/switch control example"""

        # Case1: Set IC channel gain without common gain
        # logger.info("Set Gain of IC: %s" %service.setIcChannelGain(sn, board, [gain_max,gain_max,gain_max,gain_max]))

        # Case2: Set IC channel gain with common gain, and gain means element gain(offset) if assign common gain
        # Each element gain must between 0 and common_gain_rng if using common gain
        ele_offsets = [ele_dr_limit, ele_dr_limit, ele_dr_limit, ele_dr_limit]
        logger.info("Set Gain of IC: %s" %service.setIcChannelGain(sn, 1, ele_offsets, common_gain_max))

        # input("WAIT.........Set Gain/Phase")
        # logger.info("Set Gain/Phase: %s" %service.setChannelGainPhase(sn, 1, gain_max, 30))

        # # Disable specific channel example
        # input("WAIT.........Channel Control - Disable")
        # logger.info("Disable channel: %s" %service.switchChannel(sn, 1, True))
        # logger.info("Disable channel: %s" %service.switchChannel(sn, 6, True))

        # input("WAIT.........Channel Control - Enable")
        # logger.info("Enable channel: %s" %service.switchChannel(sn, 1, False))
        # logger.info("Enable channel: %s" %service.switchChannel(sn, 6, False))

    # Beam control example
    if testBeam:
        if aakit_selected:
            input("WAIT.........Beam Control")
            # Passing: gain, theta, phi
            logger.info("SetBeamAngle-1: %s" %service.setBeamAngle(sn, gain_max, 0, 0))
            logger.info("SetBeamAngle-2: %s" %service.setBeamAngle(sn, gain_max, 10, 30))
            logger.info("SetBeamAngle-3: %s" %service.setBeamAngle(sn, gain_max, 2, 180))
        else:
            logger.error("PhiA mode cannot process beam steering")

    if testFBS:
        # Fast Beam Steering control example
        input("WAIT.........Fast Beam Steering Mode")
        # Beam pattern functions:
        logger.info("BeamId limit: %s" %service.getBeamIdStorage(sn))

        batch_import = False
        if batch_import:
            batch = TMYBeamConfig(sn, service)
            if not batch.applyBeams():
                logger.error("Beam Config setting failed")
                return
        else:
            if aakit_selected:
                # Custom beam config
                beamID = 1
                # Another way to setting
                #   args = {'beamId': beamID, 'mode': RFMode.TX, 'sn': sn}
                #   ret = service.getBeamPattern(**args)
                ret = service.getBeamPattern(sn, RFMode.TX, beamID)
                beam = ret.RetData
                logger.info("BeamID %d info: %s" %(beamID, beam))

                # Edit to beam config
                config = {}
                config['db'] = gain_max
                config['theta'] = 10
                config['phi'] = 30
                ret = service.setBeamPattern(sn, RFMode.TX, beamID, BeamType.BEAM, config)
                if ret.RetCode is not RetCode.OK:
                    logger.error(ret.RetMsg)
                    return

            # Custom channel config
            beamID = 2
            ret = service.getBeamPattern(sn, RFMode.TX, beamID)
            beam = ret.RetData
            logger.info("BeamID %d info: %s" %(beamID, beam))
            if beam.get('channel_config') is None:
                config = {}
            else:
                # Extends original config
                config = beam['channel_config']

            # Edit board 1
            # Assign random values for each channel in board_1, please modify to your case.

            # Common gain
            config['board_1']['common_db'] = common_gain_max-1
            # CH1
            config['board_1']['channel_1']['db'] = ele_dr_limit-3
            config['board_1']['channel_1']['deg'] = 190
            # CH2
            config['board_1']['channel_2']['db'] = ele_dr_limit-2
            config['board_1']['channel_2']['deg'] = 20
            # CH3
            config['board_1']['channel_3']['sw'] = 1
            # CH4
            config['board_1']['channel_4']['db'] = ele_dr_limit-4
            ret = service.setBeamPattern(sn, RFMode.TX, beamID, BeamType.CHANNEL, config)
            if ret.RetCode is not RetCode.OK:
                logger.error(ret.RetMsg)
                return

        # Set BBox to FBS mode
        service.setFastParallelMode(sn, True)
        logger.info("Fast Beam Steering Mode done")

def testBBoard(sn, service):
    logger.info("Static IP: %s" %service.queryStaticIP(sn))
    mode = RFMode.TX
    logger.info("Set RF mode: %s" %service.setRFMode(sn, mode).name)
    logger.info("Get RF mode: %s" %service.getRFMode(sn))

    ret = service.queryHWVer(sn)
    if "Unknown" in ret.RetData:
        logger.info("No HW ver")
        freq_list = service.getFrequencyList(sn).RetData
        if len(freq_list) == 0:
            logger.error("CAN NOT find your calibration files in \'files\' -> exit")
            return
        logger.info("Available frequency list: %s" %freq_list)

        # Please edit your target freq
        target_freq = 28.0
        if target_freq not in freq_list:
            logger.error("Not support your target freq:%f in freq list!")
        else:
            ret = service.setOperatingFreq(sn, target_freq)
            logger.info("Set freq: %s" %ret.RetCode)
            logger.info("Get freq: %s" %service.getOperatingFreq(sn))
            logger.info("Cali ver: %s" %service.queryCaliTableVer(sn))

            # Gain setting for BBoxOne/Lite
            rng = service.getDR(sn, mode).RetData
            logger.info("DR range: %s" %rng)

            # [Optional] Select AAKit, please call getAAKitList() to fetch all AAKit list in files/
            aakit_selected = False
            aakitList = service.getAAKitList(sn).RetData
            for aakit in aakitList:
                if 'TMYTEK_28LITE_4x4' in aakit:
                    logger.info("Select AAKit: %s, return %s" %(aakit, service.selectAAKit(sn, aakit).name))
                    aakit_selected = True
                    break
            if not aakit_selected:
                logger.warning("PhiA mode")
            else:
                gain = rng[1]
                # Passing: gain, theta, phi
                logger.info("SetBeamAngle: %s" %service.setBeamAngle(sn, gain, 10, 30))
        return
    else:
        logger.info("HW Ver: %s" %ret.RetData)

    logger.info("TC ADC: %s" %service.getTemperatureADC(sn))
    # It's a list inlcudes [TXC, TXQ, RXC, RXQ]
    service.setTCConfig(sn, [8, 6, 2, 9])

    input("WAIT.........Channel Control - Disable")

    # Disable specific channel
    logger.info("Disable channel: %s" %service.switchChannel(sn, 1, True))
    logger.info("Disable channel: %s" %service.switchChannel(sn, 4, True))

    input("WAIT.........Channel Control - Enable")

    logger.info("Enable channel: %s" %service.switchChannel(sn, 1, False))
    logger.info("Enable channel: %s" %service.switchChannel(sn, 4, False))

    input("WAIT.........Set Gain/Phase by steps")

    logger.info("Set common gain step: %s" %(service.setComGainStep(sn, 9)))
    ch = 1
    ps = 2
    gs = 8
    logger.info("Set ch%d with phase step(%d): %s" %(ch, ps, service.setChannelPhaseStep(sn, ch, ps)))
    logger.info("Set ch%d with gain step(%d): %s" %(ch, service.setChannelGainStep(sn, ch, gs)))
    ch = 3
    ps = 3
    gs = 7
    logger.info("Set ch%d with phase step(%d): %s" %(ch, ps, service.setChannelPhaseStep(sn, ch, ps)))
    logger.info("Set ch%d with gain step(%d): %s" %(ch, service.setChannelGainStep(sn, ch, gs)))

def startBFDFU(sn, service, dfu_image:str):
    """A example to process BBox series DFU"""
    ver = service.queryFWVer(sn).RetData

    ret = service.processDFU(sn, dfu_image)
    if ret.RetCode is not RetCode.OK:
        logger.error("[DFU] BBox DFU failed -> quit")
        return

    ver_new = service.queryFWVer(sn).RetData
    logger.info("[DFU] Done! FW ver: %s -> %s" %(ver, ver_new))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("--dc", help="Direct connect device to skip scanning, must provide 3 parameters: SN IP dev_type", metavar=('SN','Address','DevType'), nargs=3)
    parser.add_argument("--dfu", help="DFU image path", type=str, default="")
    parser.add_argument("--root", help="The root path/directory of for log/ & files/", type=str, default=".")
    args = parser.parse_args()

    startService(args.root, args.dc, args.dfu)
    logger.info("end")
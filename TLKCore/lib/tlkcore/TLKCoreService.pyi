# tlkcore/TLKCoreService.pyi
# this is an interface file for the TLKCoreService class

from typing import Literal, TypedDict
from enum import Enum, Flag, auto

from .TMYPublic import  DevInterface, RFMode, BeamType, RetCode, \
                        UDFreq, UDState, UDMState, UDM_SYS, UD_PLO, UD_REF, UDM_LICENSE

class Response(TypedDict):
    RetCode: RetCode
    RetMsg: str | None # not sure if all responses will have a message
    RetData: list | dict | None # not sure if all responses will have data

class TLKCoreService:
    '''This is an abstract class that interfaces with the TymTek API'''

    # GENERAL METHODS ---------------------------------------------------------
    def __init__(self, path=".") -> None:
        '''Initializes the TLKCoreService object with the given path, DefaultPath=\".\"'''
        ...

    def queryTLKCoreVer(self) -> str:
        '''Returns the version of the TLKCoreService'''
        ...

    def scanDevices(self, interface:DevInterface) -> Response:
        '''Scans for devices with the given interface
        \ninterface: DevInterface = {ALL, LAN, COMPORT, USB}
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: list}'''
        ...

    def getScanInfo(self, *args) -> Response:
        '''Returns a Response dictionary containing the scan information

        also accepts a serial_number:str argument to get the scan info for a specific device

        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: dict}
        \nRetData = {SerialNumber: (Address, DeviceType)}'''
        ...

    def initDev(self, serialNumber:str) -> Response:
        '''Initializes the device with the given serial number
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: ?}'''
        ...

    def getDevTypeName(self, serialNumber:str) -> str:
        '''Returns the device type name of the device with the given serial number'''
        ...
    
    def querySN(self, serialNumber:str) -> str:
        '''Returns the serial number of the device with the given serial number
        \n...HUH?'''
        ...

    def queryFWVer(self, serialNumber:str) -> str:
        '''Returns the firmware version of the device with the given serial number'''
        ...
    
    def queryHWVer(self, serialNumber:str) -> str:
        '''Returns the hardware version of the device with the given serial number'''
        ...

    def DeInitDev(self, serialNumber:str) -> Response:
        '''DEPRECIATED OR NOT WORKING!
        \nDe-initializes the device with the given serial number
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: ?}'''
        ...

    # UDBOX METHODS -----------------------------------------------------------
    # (only for UDBOX devices)
    def getUDState(self, serialNumber:str, UDState:UDState|None) -> Response:
        '''Returns the UDstate of the device with the given serial number
        \nUDState = {PLO_LOCK, CH1, CH2, OUT_10M, OUT_100M, SOURCE_100M, LED_100M, PWR_5V, PWR_9V}
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: UDState | List}'''
        ...

    def setUDState(self, serialNumber:str, value:Enum|Flag|int|bool, state:UDState) -> dict:
        '''Sets the UDstate of the device with the given serial number.
        The state:UDstate can be: PLO_LOCK, CH1, CH2, OUT_10M, OUT_100M, SOURCE_100M, LED_100M, PWR_5V, PWR_9V
        The value:Enum|Flag can be: UD_REF, or a 0/1 for CH1/CH2 (1 is on)
        \nReturns the full new UDState of the device as a dictionary'''
        ...

    def getHarmonic(self, serialNumber:str, 
                    LocalOscillator:float, RadioFrequency:float,
                    IntermediateFrequency:float, BandWidth:float) -> Response:
        '''Returns True (RetData) if any bad harmonics are detected, False otherwise
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: bool}'''
    
    def setUDFreq(self, serialNumber:str,
                  LocalOscillator:float, RadioFrequency:float,
                  IntermediateFrequency:float, BandWidth:float) -> Response:
        '''Sets the frequency of the device with the given serial number
        \n(LO, RF, IF, BW), (checks harmonics before applying the settings)
        \nall frequencies are in KHz
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: bool}'''

    def getUDFreq(self, serialNumber:str) -> dict|UDFreq:
        '''Returns the current \'frequency setting\' of the device with the given serial number
        \n(WARNING: This does not return the actual frequency values, but the current settings)
        \nThis method does not seem to be consistant with the UDFreq Enum???
        \nUDFreq = {UDFreq, RFFreq, IFFreq}'''
        ...

    # BBBOX METHODS -----------------------------------------------------------
    # (only for BBBOX devices)
    def setRFMode(self, serialNumber:str, rfMode:RFMode) -> RFMode:
        '''Sets the RFMode of the BBox device with the given serial number
        \nRFMode = {TX, RX}
        \nReturns the new RFMode (HINT: use ".name" to get the string value)'''
        ...

    def getFrequencyList(self, serialNumber:str) -> Response:
        '''Returns the frequency list supported by the device/calibrationFiles with the given serial number
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: List}
        (HINT: use ".RetData" to get the list)'''
        ...

    def setOperatingFreq(self, serialNumber:str, targetFrequency:float) -> Response:
        '''Sets the operating frequency of the device with the given serial number
        \nThe targetFrequency is in Ghz with 1 decimal place (ex: 28.0)
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: ?}'''
        ...

    def getOperatingFreq(self, serialNumber:str) -> float:
        '''Returns the current operating frequency of the device with the given serial number
        \nThe frequency is in Ghz with 1 decimal place (ex: 28.0)'''
        ...

    def queryCaliTableVer(self, serialNumber:str) -> str:
        '''Returns the calibration table version of the device with the given serial number
        \n(ex: "2.3.7")'''
        ...
    
    def getDR(self, serialNumber:str, TX_RX_mode:RFMode) -> Response:
        '''Returns the Dynamic Range (gain min/max) of the device with the given serial number
        \nmode = {TX, RX}
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: List[min,max]}'''
        ...
    
    def getCOMDR(self, serialNumber:str) -> Response:
        '''Returns the COMmon Dynamic Range (gain min/max) of the device with the given serial number
        \nthis returns a list of lists of list for the entire device [tx/rx [min,max]] for each "board"
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: ex.List[List[List[min,max]]]}
        \n(HINT: use ".RetData" to get the listsss and RFMode to access the correct index)'''
        ...

    def getELEDR(self, serialNumber:str) -> Response:
        '''Returns the ELEment-wise Dynamic Range (gain limit) of the device with the given serial number
        \nthis returns a list of lists for the entire device [tx/rx [limit]] for each "board"
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: ex.List[List[min,max]]}
        \n(HINT: use ".RetData" to get the listss and RFMode to access the correct index)'''
        ...

    def getAAKitList(self, serialNumber:str) -> Response:
        '''Returns the list of AAKit found/supported by the device with the given serial number
        \nthe AAKit files are within the "file" directory
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: List}'''
        ...
        
    def selectAAKit(self, serialNumber:str, AAKitName:str) -> Response:
        '''Selects the AAKit with the given name for the device with the given serial number
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: ?}
        \n(HINT: .name gives the string value of the RetCode, ex: "OK")'''
        ...

    def getBoardCount(self, serialNumber:str) -> int:
        '''Returns the number of boards in the device with the given serial number'''
        ...
    
    def setBeamAngle(self, serialNumber:str, gain:float, theta:float, phi:float) -> Response:
        '''Sets the beam angle of the device with the given serial number
        \ntheta and phi are in degrees
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: ?}'''
        ...
    
    def setIcChannelGain(self, serialNumber:str, channel:int ,eleOffsetLimit:list[float], commonGainMax:float):
        '''WARNING:UNTESTED! - Sets the IC channel gain of the device with the given serial number
        \nchannel = {1, 2, ...} (THIS IS UNEXPLORED, 1 indexed?)
        \neleOffsetLimit = [float, float, float, float], this is a list of 4 floats, given from ELEDR
        \ncommonGainMax = float, given from COMDR
        \nResponse = UNKNOWN'''
        ...
    
    def setChannelGainPhase(self, serialNumber:str, channel:int, gain:float, phase:int):
        '''WARNING:UNTESTED! - Sets the channel gain and phase of the device with the given serial number
        \nchannel = {1, 2, ...} (THIS IS UNEXPLORED, 1 indexed? 16 channels?)
        \ngain = float
        \nphase = (THIS IS UNEXPLORED, int? float?)
        \nResponse = UNKNOWN'''
        ...

    def switchChannel(self, serialNumber:str, channel:int, state:bool):
        '''Disables the channel of the device with the given serial number
        \nchannel = {1, 2, ...} (THIS IS UNEXPLORED, 1 indexed?)
        \nstate = {True, False} (True disables the channel)
        \nResponse = UNKNOWN'''
        ...

    def getTemperatureADC(self, serialNumber:str) -> Response:
        '''Returns the temperature ADC value of the device with the given serial number
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: List[board1, board2, ...]}'''
        ...

    # fast beam steering 
    def getBeamIdStorage(self, serialNumber:str):
        '''UNTESTED, seems to return the BeamId limit, int?, both tx/rx?'''
        ...
    # TMYBeamConfig(.py) directly applies a csv file to the device it is not a service method
    # ex. "TMYBeamConfig.applyBeams()""
    def getBeamPattern(self, serialNumber:str, TX_RX_mode:RFMode, beamID:int) -> Response:
        '''Returns the beam dictionary for the beamID, this is stored on the device
        \nTX_RX_mode = {TX, RX}
        \ndict = UNKNOWN keys, likely {db, theta, phi, ...}
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: dict}'''
        ...
    
    def setBeamPattern(self, serialNumber:str, beamID:int, beamType:BeamType, config:dict) -> Response:
        '''Sets the beam dictionary for the beamID, this is stored on the device
        \nbeamID = beam index (int)
        \nbeamType = {BEAM, CHANNEL}
        \nconfig = {db, theta, phi, channel_config} "channel_config" is a hierarchical dict of
        \n\teach of each board,channel,setting -- 'board_1' and 'common db', 'channel_1' and 'db','deg','sw'
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: ?}'''
        ...

    def setFastParallelMode(self, serialNumber:str, FBSState:bool) -> Response:
        '''Sets the fast beam steering parallel mode of the device with the given serial number
        \nFBSState = {True, False}
        \nResponse = {RetCode: RetCode, RetMsg: ?, RetData: ?}'''
        ...
    
    

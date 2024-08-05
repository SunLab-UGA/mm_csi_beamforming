# this is the main file for producing a beamscan with the Tymtek wrapper and sdr 802_11 csi data

import argparse
import logging
import logging.config
import os
from pathlib import Path
import platform
import sys
import time
import traceback
import numpy as np
import zmq


from tymtek_wrapper import TMY_service, UDBox, BBox5G # TymTek wrapper
from gnu_manager import GNURadioManager # start and stop the GNU Radio process
from trans import transceiver # send and receive data from the GNU Radio process

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

# from tlkcore.TLKCoreService import TLKCoreService
# from tlkcore.TMYBeamConfig import TMYBeamConfig
from tlkcore.TMYPublic import DevInterface,RetCode,RFMode,UDState,UDMState,BeamType,UD_REF 
logging.info("Successfully Imported TLKCoreServices")

# ----------------------------------------------------------------------- END OF IMPORTS

if __name__ == "__main__":
    print("=== Welcome! ===")
    # create a service object
    service = TMY_service()

    serials = ['UD-BD22470039-24','D2245E028-28','D2245E027-28']
    aakits = [None, 'TMYTEK_28ONE_4x4_C2245E029-28', 'TMYTEK_28ONE_4x4_C2245E030-28'] # antenna kit for device
    logger.info("Looking for Devices with serial numbers: %s" %serials)

    udbox:UDBox; txbbox:BBox5G; rxbbox:BBox5G # typehinting for the devices
    service = TMY_service(serial_numbers=serials)
    # get the devices from the service
    udbox, txbbox, rxbbox = service.devices

    freq_list = [28_000_000, 25_548_000, 2_452_000, 50_000]
    if udbox.basic_setup(freq_list): logger.info("UDBox setup complete")
    else: logger.error("UDBox setup failed")

    # setup the BBoxOne5G devices
    if txbbox.basic_setup(28.0, RFMode.TX, aakits[1]): logger.info("TX BBoxOne5G setup complete")
    else: logger.error("TX BBoxOne5G setup failed")
    if rxbbox.basic_setup(28.0, RFMode.RX, aakits[2]): logger.info("RX BBoxOne5G setup complete")
    else: logger.error("RX BBoxOne5G setup failed")

    # setup GNU Radio
    conda_env = "radio_base"
    path = "/home/sunlab/radioconda/share/gnuradio/examples/ieee802_11"
    python_filename = "wifi_transceiver_nogui.py"
    gnu_service = GNURadioManager(conda_env=conda_env, path=path, python_filename=python_filename)
    gnu_service.start()

    # wait for the GNU Radio to start
    logger.info("Waiting for GNU Radio to start")
    time.sleep(10) # typically less but cold start may take longer

    if gnu_service.poll() is not None: # poll the process to check if it is still running
        logger.error("GNU Radio failed to start")
        exit(1)

    # make both devices boresight
    logger.info("Setting BBoxOne5G devices to boresight")
    txbbox.boresight()
    logger.info(f"{txbbox.serial_number} set to {txbbox.beam}")
    rxbbox.boresight()
    logger.info(f"{rxbbox.serial_number} set to {rxbbox.beam}")

    # transmit and receive a packet
    logger.info("Transmitting and receiving a packets")
    trans = transceiver(tx_port=64001, rx_port=64000)
    for i in range(5):
        pdu = f"HELLOW SUNLAB {i+1}!"
        logger.info(f"Transmitting packet: {pdu}")
        trans.send(pdu)
        rx = trans.recieve_csi(timeout=10)
        if rx is not None:
            logger.info("Received CSI data")
            logger.debug(rx)
        else:
            logger.error("Failed to receive CSI data")
        time.sleep(0.25)


    logger.info("Disabling UDBox channels")
    udbox.disable_channels() # disable both channels
    gnu_service.stop() # stop the GNU Radio process


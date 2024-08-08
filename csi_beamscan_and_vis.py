# this is a stub for a script that will be used to automate the beamscan and image generation

# for now this is a copy of csi_beamscan.py with added functionality from csi_beamscan_vis.py

import logging
import logging.config
import os
from pathlib import Path
import platform
import sys
import time
import numpy as np
import pickle


from tymtek_wrapper import TMY_service, UDBox, BBox5G # TymTek wrapper
from gnu_manager import GNURadioManager # start and stop the GNU Radio process
from trans import transceiver # send and receive data from the GNU Radio process

from csi_beamscan_vis_gp import convert_to_cartesian

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
    serials = ['UD-BD22470039-24','D2245E027-28','D2245E028-28'] #udbox, txbox, rxbox
    aakits = [None, 'TMYTEK_28ONE_4x4_C2245E029-28', 'TMYTEK_28ONE_4x4_C2245E030-28'] # antenna kit for device
    logger.info("Looking for Devices with serial numbers: %s" %serials)

    udbox:UDBox; txbbox:BBox5G; rxbbox:BBox5G # typehinting for the devices
    service = TMY_service(serial_numbers=serials)
    if len(service.devices) != len(serials): logger.error("Failed to find all devices");exit(1)
    # get the devices from the service, will be in the order of the serials
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
    time.sleep(4.5) # typically less but cold start may take longer! 

    if gnu_service.poll() is not None: # poll the process to check if it is still running
        logger.error("GNU Radio failed to start")
        exit(1)

    # make both devices boresight
    logger.info("Setting BBoxOne5G devices to boresight")
    txbbox.boresight()
    logger.info(f"{txbbox.serial_number} set to {txbbox.beam}")
    rxbbox.boresight()
    logger.info(f"{rxbbox.serial_number} set to {rxbbox.beam}")

    # perform a beamscan
    csi_data = []
    theta_step = 5; phi_step = 20
    rx_scanner = rxbbox.scan_raster_generator(theta_step=theta_step, phi_step=phi_step)
    # check if the scanner is did not return None (indicating an error)
    if rx_scanner is None: logger.error("Failed to generate the scan raster");exit(1)

    trans = transceiver(tx_port=64001, rx_port=64000)
    packets_per_beam = 2
    # BEAMSCAN --------------------------------------------------------------------------
    logger.info("Performing beamscan")
    start_time = time.time()
    for i, scanning in enumerate(rx_scanner):
        logger.debug(f'beam {i}: scanning {scanning}')
        if scanning is None: logger.info("scan ended");break # break if the scan is complete
        # logger.debug(f"beam {i}: {rxbbox.serial_number} set to {rxbbox.beam}")
        # transmit and receive a packet
        beam_data = {}
        for ii in range(packets_per_beam):
            pdu = f"HELLO SUNLAB {ii+1}!"
            beam_data['pdu'] = pdu
            beam_data['beam'] = rxbbox.beam # store the beam [gain, theta, phi]
            logger.debug(f"Transmitting packet: {pdu}")
            trans.send(pdu)
            beam_data['timestamp'] = time.time()
            time.sleep(0.001) # 1ms
            rx = trans.recieve_csi(timeout=7) # timeout in ms
            if rx is not None:
                logger.debug("Received CSI data")
                beam_data['csi'] = rx
                # process the CSI data into an average
                avg_csi = np.mean(rx, axis=0)
                beam_data['avg_csi'] = avg_csi
                logger.debug(f'avg_csi: {avg_csi}')
            else:
                logger.debug("Failed to receive CSI data")
                beam_data['csi'] = None
                beam_data['avg_csi'] = None
            csi_data.append(beam_data)
            time.sleep(0.010) # 10ms
    end_time = time.time()
    beamscan_time = end_time - start_time
    logger.info(f"Time taken: {beamscan_time} seconds")
    logger.info("Disabling UDBox channels")
    udbox.disable_channels() # disable both channels
    gnu_service.stop() # stop the GNU Radio process

    # save the data to a pickle file
    logger.info("len(csi_data): %d" %len(csi_data))
    logger.info("Saving the data to a pickle file")
    time_suffix = time.strftime("%Y%m%d-%H%M%S")
    filename = f'csi_data_{time_suffix}.pkl'
    with open(filename, 'wb') as file:
        pickle.dump(csi_data, file)
    logger.info(f"Data saved to {filename}")


    logger.info(f"Parameters saved to {filename}")
    logger.info("=== Scan Done! ;D ===")




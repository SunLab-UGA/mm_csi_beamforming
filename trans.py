# this class tracks the address and ports and setup of zmq which is used to communicate with the gnu radio process

import zmq
import pmt
import numpy as np

class transceiver:
    '''This class tracks the address and ports and setup of zmq which is used to communicate with the gnu radio process'''
    def __init__(self, address:str='127.0.0.1', tx_port:int|None=None, rx_port:int|None=None):
        '''Initializes the transceiver object with the given address and ports for tx and rx
        tx_port is the port to send data to the gnu radio process
        rx_port is the port to receive data from the gnu radio process'''
        self.address = address
        self.tx_port = tx_port
        self.rx_port = rx_port

        self.context = zmq.Context()
        if tx_port is not None:
            self.tx_socket = self.context.socket(zmq.PUSH)
            self.tx_socket.bind(f"tcp://{self.address}:{self.tx_port}")
        if rx_port is not None:
            self.rx_socket = self.context.socket(zmq.PULL)
            self.rx_socket.connect(f"tcp://{self.address}:{self.rx_port}")
            # self.rx_socket.setsockopt_string(zmq.SUBSCRIBE, "")

    def send(self, message:str):
        '''Sends the given message to the gnu radio process'''
        msg = pmt.to_pmt(message)
        serialized_msg = pmt.serialize_str(msg)
        self.tx_socket.send(serialized_msg)
    
    def recieve_csi(self, timeout:int=10): # recieve a csi message (array of complex64)
        '''Receives a message from the gnu radio process
        timeout will wait X ms for a message before returning None'''
        if self.rx_socket.poll(timeout, zmq.POLLIN):
            serialized_msg = self.rx_socket.recv()
            data = np.frombuffer(serialized_msg, dtype=np.complex64, count=-1) # as complex64, count=-1 is all data
            return data # return none if no data is implicit
    


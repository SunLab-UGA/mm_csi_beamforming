# this are different generator functions for producing a beam of phi and theta values in the beamfile_gen.py

import numpy as np
from dataclasses import dataclass, field
from typing import Tuple, List

@dataclass
class Beam_params:
    '''Beam parameters constants for generating beams'''
    THETA_LIMIT: float = 45 # available degrees for scanning (0-45)
    PHI_LIMIT: float = 359 # available degrees for scanning (0-359)
    TX_LIMIT: Tuple[float, float] = (-5.5, 12) # range in dB
    RX_LIMIT: Tuple[float, float] = (-15.5, 4.5) 
    MAX_BEAMS: int = 64 # maximum beams to generate


def generate_beams(theta_step: float = 5, phi_step: float = 5, beam_params: Beam_params = Beam_params()) -> List[Tuple[int,int]]:
    '''
    Generate beams based on the beam parameters (a zip of theta and phi values, including the bore sight beam)
    Returns a list of beams with theta and phi values
    '''
    beams = []

    # append bore sight beam
    beams.append((0, 0))

    _e = 1e-10 # make arange inclusive
    theta = [i for i in np.arange(theta_step, Beam_params.THETA_LIMIT+_e, theta_step)] # start from theta_step to avoid duplicate bore sight beam
    phi = [i for i in np.arange(0, Beam_params.PHI_LIMIT+_e, phi_step)]

    # zip theta and phi values
    for t in theta:
        for p in phi:
            beams.append((t, p))
    
    return beams
    

if __name__ == "__main__":

    beam_params = Beam_params()

    # beams = generate_beam(num_beams, theta_limit, phi_limit, tx_limit, rx_limit, max_beams)
    print(beam_params)

    beams = generate_beams(theta_step=5, phi_step=20, beam_params=beam_params)
    print("Generated beams: ")
    print(f'len of beams: {len(beams)}')
    print(np.array(beams))
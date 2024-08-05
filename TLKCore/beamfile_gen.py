# this is used to create a csv file with the appropriate beam configuration for scanning a spactial area (ie spactial spectrum)

# theta is a polar angle from down the Z (or bore) axis of the beamformer
# phi is a azimuth angle on the xy-plane

import os
import sys
import csv
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.cm as cm

from beamfile_util import Beam_params, generate_beams

# struct for beam parameters
beam_params = Beam_params() # default values
print(beam_params)

# get the beam values
beams = generate_beams(theta_step=5, phi_step=20, beam_params=beam_params)
print("Generated beams: ")
print(f'len of beams: {len(beams)}')
print()
# print the first 5 beams and the last 5 beams
print(f'first 5 beams:\n {beams[:5]}')
print(f'last 5 beams:\n {beams[-5:]}')


def plot_theta_phi(theta_samples, phi_samples):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Convert spherical coordinates to Cartesian coordinates for plotting
    theta_rad = np.deg2rad(theta_samples)
    phi_rad = np.deg2rad(phi_samples)
    x = np.sin(theta_rad) * np.cos(phi_rad)
    y = np.sin(theta_rad) * np.sin(phi_rad)
    z = np.cos(theta_rad)
    colors = cm.viridis(theta_samples / np.max(theta_samples))
    ax.scatter(x, y, z, c=colors, marker='o', s=10)
    # Set equal scaling
    max_range = np.array([x.max()-x.min(), y.max()-y.min(), z.max()-z.min()]).max() / 2.0
    mid_x = (x.max() + x.min()) * 0.5
    mid_y = (y.max() + y.min()) * 0.5
    mid_z = (z.max() + z.min()) * 0.5
    ax.set_xlim(mid_x - max_range, mid_x + max_range)
    ax.set_ylim(mid_y - max_range, mid_y + max_range)
    ax.set_zlim(mid_z - max_range, mid_z + max_range)
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    plt.show()

# init and header
data = [["Mode","BeamID","BeamType","beam_db","beam_theta","beam_phi","ch","ch_sw","ch_db","ch_deg"]]

# by row add a beam
for beam_num, beam in enumerate(beams):
    data.append(["tx", beam_num+1, 0, "db", beam[0], beam[1], "", "", "", ""]) # beamindex starts from 1


# pretty print
print()
for row in data:
    print(row)

# write to csv
with open('beamfile.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows(data)

# this loads the csi_data_[datetime].pkl file and visualizes the data

import pickle
import plotly.graph_objects as go
import glob
import os
import time
import numpy as np

def find_recent_file():
    '''find the most recent .pkl file in the current directory'''
    list_of_files = glob.glob('*.pkl') # * means all if need specific format then *.csv
    if len(list_of_files) == 0:
        print("no pkl files found in the current directory")
        return None
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file

def load_csi(file) -> list[dict]:
    '''load the csi data from the pickle file'''
    with open(file,'rb') as file:
        data = pickle.load(file)

    # sanity check the type of the fist element in the list, should be a dictionary
    # warn the user if it is not a dictionary
    if not isinstance(data[0], dict):
        print("the data is not a list of dictionary, please check the pickle file")
    return data

def plot_figure_3d_cart(theta, phi, avg_csi_mag, filename, save=True, show=True):
    '''plot the 3d figure of the beamscan data as a 3d scatter plot (very basic)'''
    fig = go.Figure()

    fig.add_trace(go.Scatter3d(
        x=theta,
        y=phi,
        z=avg_csi_mag,
        mode='markers', # only plot the points or 'markers'
        marker=dict(
            size=5,
            color=avg_csi_mag,  # Color by magnitude
            colorscale='Viridis',  # Choose a colorscale
            opacity=0.8
        )
    ))
    # Add labels
    fig.update_layout(
        scene=dict(
            xaxis_title='Theta',
            yaxis_title='Phi',
            zaxis_title='CSI AVG Magnitude'
        ),
        title='Beamscan Data Visualization'
    )
    if save:
        # save the plot, remove the suffix of the pickle file and add .html
        filename = filename.split('.')[0]; filename = filename+'_cart.html'
        fig.write_html(filename)
        print(f"plot saved to {filename}")
    if show:
        fig.show()

def plot_figure_3d_sphere(theta, phi, avg_csi_mag, filename, save=True, show=True, mag_as_z=False):
    '''use the spherical coordinates to plot the beamscan data on a sphere
    if mag_as_z is False, the data will be plotted on a sphere (only the color will show the magnitude)
    if mag_as_z is True, the data will be plotted on disk with the z-axis as the magnitude'''
    # Convert spherical coordinates to Cartesian coordinates for plotting
    theta_rad = np.deg2rad(theta); phi_rad = np.deg2rad(phi)
    x = np.sin(theta_rad) * np.cos(phi_rad)
    y = np.sin(theta_rad) * np.sin(phi_rad)
    # if mag_as_z is False, use the cos of theta as the z-axis
    z = avg_csi_mag if mag_as_z else np.cos(theta_rad) 

    fig = go.Figure()
    fig.add_trace(go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode='markers', # only plot the points or 'markers'
        marker=dict(
            size=5,
            color=avg_csi_mag,  # Color by magnitude
            colorscale='Viridis',  # Choose a colorscale
            opacity=0.8
        )
    ))
    
    if not mag_as_z: # if mag_as_z is False make the z-axis scaling equal to the x and y axis
        max_range = np.array([x.max()-x.min(), y.max()-y.min(), z.max()-z.min()]).max() / 2.0
        mid_x = (x.max() + x.min()) * 0.5
        mid_y = (y.max() + y.min()) * 0.5
        mid_z = (z.max() + z.min()) * 0.5

    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[mid_x - max_range, mid_x + max_range]) if not mag_as_z else dict(),
            yaxis=dict(range=[mid_y - max_range, mid_y + max_range]) if not mag_as_z else dict(),
            zaxis=dict(range=[mid_z - max_range, mid_z + max_range]) if not mag_as_z else dict(),
            xaxis_title='X',
            yaxis_title='Y',
            zaxis_title='Z'
        ),
        title='Beamscan Data Visualization on Sphere'
    )
    if save:
        z_axis = 'mag' if mag_as_z else 'cos_theta'
        # save the plot, remove the suffix of the pickle file and add .html
        filename = filename.split('.')[0]; filename = filename+f'_sphere_z_{z_axis}.html'
        fig.write_html(filename)
        print(f"plot saved to {filename}")
    if show:
        fig.show()


if __name__ == "__main__":
    # find the most recent .pkl file in the current directory
    print("finding most recent file")
    latest_file = find_recent_file()
    if latest_file is None:print("no file found, exiting");exit(1) # exit if no file is found
    # override the latest_file if you want to load a specific file
    # latest_file = 'csi_data_20240722-170149.pkl'
    print(f"loading file: {latest_file}")
    data = load_csi(latest_file)
    print("data loaded")

    # print the keys in the first dictionary and the value type
    print("keys in the first dictionary and the value type:")
    for key, value in data[0].items():
        print(f"key: '{key}', value type: {type(value)}")
        if isinstance(value, np.ndarray):
            print(f"\tshape: {value.shape}")
        if isinstance(value, list):
            print(f"\tlength: {len(value)}")
        if isinstance(value, dict):
            print(f"\tkeys: {value.keys()}")
        if isinstance(value, str):
            print(f"\tfirst value: {value}")

    # extract the plot data
    theta = []
    phi = []
    avg_csi_mag = []
    for entry in data:
        if entry['avg_csi'] is None: # check if the avg_csi contains None (the packet was not received)
            # continue # skip the entry
            avg_csi_mag.append(0)
        else:
            avg_csi_mag.append(np.abs(entry['avg_csi']))
        theta.append(entry['beam']['theta']) 
        phi.append(entry['beam']['phi'])

    print("data extracted")
    print(f'len of data: {len(avg_csi_mag)}')    
    print("plotting")

    # plot_figure_3d_cart(theta, phi, avg_csi_mag, latest_file, save=True, show=True)
    
    plot_figure_3d_sphere(theta, phi, avg_csi_mag, latest_file, 
                          save=True, show=True, mag_as_z=True)
    time.sleep(1)

    plot_figure_3d_sphere(theta, phi, avg_csi_mag, latest_file, 
                        save=True, show=True, mag_as_z=False)


    print("done")
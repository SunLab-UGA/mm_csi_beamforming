# this loads the csi_data_[datetime].pkl file and visualizes the data
# with a GP to predict the full spatial spectrum of the beamscan from previous scan data

import pickle
import plotly.graph_objects as go
import plotly.express as px
import glob
import os
import time
import numpy as np

from itertools import product

from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, Matern, WhiteKernel, ConstantKernel as C
from sklearn.gaussian_process.kernels import Kernel

from scipy.stats import norm

import warnings
# warnings.filterwarnings("ignore") # ignore the warnings from the GP

def find_recent_file():
    '''find the most recent .pkl file in the current directory'''
    list_of_files = glob.glob('*.pkl') # * means all if need specific format then *.csv
    if len(list_of_files) == 0:
        print("no pkl files found in the current directory")
        return None
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file

def find_txt_header(file):
    '''find the header of the .txt file
    reads the first line of the file'''
    with open(file, 'r') as file:
        header = file.readline()
    return header

def load_csi(file) -> list[dict]:
    '''load the channel state information (csi) data from the pickle file'''
    with open(file,'rb') as file:
        data = pickle.load(file)

    # sanity check the type of the fist element in the list, should be a dictionary
    # warn the user if it is not a dictionary
    if not isinstance(data[0], dict):
        print("the data is not a list of dictionary, please check the pickle file")
    return data

def create_linespace(   xx_range, 
                        yy_range, # degrees (0 to phi_max)
                        resolution=1000 # number of points in the linespace
    ):
    '''create a linespace of theta and phi values
    this is used to estimate the full spatial spectrum of the beamscan
    '''
    xx = np.linspace(xx_range[0], xx_range[1], resolution)
    yy = np.linspace(yy_range[0], yy_range[1], resolution)
    aa = np.array(list(product(xx, yy)))
    return xx,yy,aa

def plot_figure_surface_gp(xx, yy, mag, title="GP Prediction of Beamscan",
                           save_filename:None|str=None, show:bool=True):
    '''plot the surface plot of the GP prediction
    xx: the linespace created for the GP prediction
    mag: the magnitude of the GP prediction
    save: if not None, save the plot to the filename
    show: if True, show the plot'''
    fig = go.Figure(data=[go.Surface(z=mag, x=xx, y=yy, colorscale='Viridis')])
    fig.update_layout(title=title,
                        autosize=True,
                        )
    if save_filename is not None:
        save_filename = save_filename.split('.')[0]; save_filename = save_filename+f'_gp_surface.html'
        fig.write_html(save_filename)
        print(f"plot saved to {save_filename}")
    if show:
        fig.show()

def plot_heatmap_gp(xx, yy, mag, title="GP Prediction of Beamscan",
                    save_filename=None, filename_suffix="",show=True):
    '''plot the heatmap of the GP prediction'''
    fig = px.imshow(mag, x=xx, y=yy, color_continuous_scale='Viridis', origin='lower', labels={'color':'Magnitude'})
    fig.update_layout(title=title,
                      autosize=True,
                      xaxis_title='X',
                      yaxis_title='Y')
    if save_filename is not None:
        save_filename = save_filename.split('.')[0] + f'_gp_heatmap{filename_suffix}.html'
        fig.write_html(save_filename)
        print(f"plot saved to {save_filename}")
    if show:
        fig.show()

def plot_scatter(xx, yy, mag, title="GP Prediction of Beamscan",
                    save_filename=None, filename_suffix="",show=True):
    '''plot data as a scatter plot'''
    fig = px.scatter(x=xx, y=yy, color=mag, labels={'color':'Magnitude'})
    fig.update_layout(title=title,
                      autosize=True,
                      xaxis_title='X',
                      yaxis_title='Y',
                      xaxis=dict(scaleanchor="y", scaleratio=1), # make the x and y axis the same scale
                      yaxis=dict(scaleanchor="x", scaleratio=1))
    if save_filename is not None:
        save_filename = save_filename.split('.')[0] + f'_gp_scatter{filename_suffix}.html'
        fig.write_html(save_filename)
        print(f"plot saved to {save_filename}")
    if show:
        fig.show()

def convert_to_cartesian(theta, phi):
    '''convert the spherical coordinates to cartesian coordinates'''
    # x = np.sin(theta) * np.cos(phi)
    # y = np.sin(theta) * np.sin(phi)
    # z = np.cos(theta)
    x = np.sin(np.deg2rad(theta)) * np.cos(np.deg2rad(phi))
    y = np.sin(np.deg2rad(theta)) * np.sin(np.deg2rad(phi))
    z = np.cos(np.deg2rad(theta))
    return x, y, z


if __name__ == "__main__":
    # override the latest_file if you want to load a specific file
    filename_override = None
    # filename_override = 'csi_data_20240723-141321.pkl'
    
    print(f"filename_override: {filename_override}") if filename_override is not None else print("no filename given")

    if filename_override is None:
        # find the most recent .pkl file in the current directory
        print("finding most recent file")
        latest_file = find_recent_file()
    else:
        latest_file = filename_override
    if latest_file is None:print("no '.plk' file found or given, exiting");exit(1) # exit if no file is found
    
    print(f"loading file: {latest_file}")
    data = load_csi(latest_file)
    try: # try to find the header of the txt file (used for the plot title)
        header = find_txt_header(latest_file.split('.')[0]+'.txt')
        print(f"header of the file: {header}")
    except:
        print("no header found")
        header = None

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
    theta_phi = []
    z_axis = []
    avg_csi_mag = []
    for entry in data:
        if entry['avg_csi'] is None: # check if the avg_csi contains None (the packet was not received)
            continue # skip the entry
            avg_csi_mag.append(0)
        else:
            avg_csi_mag.append(np.abs(entry['avg_csi']))
        # Convert spherical coordinates to Cartesian coordinates for prediction and plotting
            x, y, z = convert_to_cartesian(entry['beam']['theta'], entry['beam']['phi'])
            theta_phi.append([x, y])
            z_axis.append(z) # the z-axis here is the curvature of the sphere (if needed)
    
    # convert the lists to numpy arrays
    theta_phi = np.array(theta_phi, dtype=np.float64)
    avg_csi_mag = np.array(avg_csi_mag, dtype=np.float64)

    print("data extracted")
    print(f'len of data: {len(avg_csi_mag)}')
    print("calculating the GP")
    # kernel = C(1.0) * RBF(1.0) + WhiteKernel(1.0) # default kernel
    kernel = C(0.0224**2) * RBF(length_scale=0.179) + WhiteKernel(2.79e-05) # updated kernel
    print(f"kernel: {Kernel}")
    gp = GaussianProcessRegressor( kernel=kernel,
                                    optimizer='fmin_l_bfgs_b',
                                    n_restarts_optimizer=30,
                                    copy_X_train=True,
                                    random_state=42)
    print(f'theta_phi shape: {np.array(theta_phi).shape}, dtype: {np.array(theta_phi).dtype}')
    print(f'avg_csi_mag shape: {np.array(avg_csi_mag).shape}, dtype: {np.array(avg_csi_mag).dtype}')

    # Check for NaN or infinite values
    if np.any(np.isnan(theta_phi)) or np.any(np.isinf(theta_phi)):
        print("theta_phi contains NaN or infinite values.")
    else:
        print("theta_phi is clean (no NAN/inf values found).")

    if np.any(np.isnan(avg_csi_mag)) or np.any(np.isinf(avg_csi_mag)):
        print("avg_csi_mag contains NaN or infinite values.")
    else:
        print("avg_csi_mag is clean (no NAN/inf values found).")

    # TRAINING =================================================================================
    print("fitting the GP")
    time_start = time.time()
    gp.fit(theta_phi , avg_csi_mag)
    time_end = time.time()
    print("GP calculated")
    print(f"Time taken to fit the GP: {time_end-time_start:.2f} seconds")
    # give stats about the GP
    print(f"GP kernel_: {gp.kernel_}")
    print(f"GP log_marginal_likelihood_: {gp.log_marginal_likelihood_value_}")
    # print(f'lower-triangular L_ : {gp.L_}')
    score = gp.score(theta_phi, avg_csi_mag)
    print(f"GP R^2 score (-1 to 1) with input data: {score}")


    print("fitting the GP (matern kernel)")
    kernel_m =    C(0.025**2) * \
                Matern(length_scale=0.268, nu=2.5) + \
                WhiteKernel(noise_level=2.61e-05)
    gp_matern = GaussianProcessRegressor(   kernel=kernel_m,
                                            optimizer='fmin_l_bfgs_b',
                                            n_restarts_optimizer=30,
                                            copy_X_train=True,
                                            random_state=42)
    time_start = time.time()
    gp_matern.fit(theta_phi , avg_csi_mag)
    time_end = time.time()
    print("GP calculated")
    print(f"Time taken to fit the GP: {time_end-time_start:.2f} seconds")
    # give stats about the GP
    print(f"GP kernel_: {gp_matern.kernel_}")
    print(f"GP log_marginal_likelihood_: {gp_matern.log_marginal_likelihood_value_}")
    score = gp_matern.score(theta_phi, avg_csi_mag)
    print(f"GP R^2 score (-1 to 1) with input data: {score}")
    print()

    # PREDICTION =================================================================================
    linespace_density = 100
    # xx,yy,aa = create_linespace(xx_range=(-200,200),yy_range=(-200,200), resolution=linespace_density)
    xx,yy,aa = create_linespace(xx_range=(-1,1),yy_range=(-1,1), resolution=linespace_density)
    print("prediction linespace created")
    yy_pred, yy_sigma = gp.predict(aa, return_std=True)
    print("GP predicted")

    # reshape the prediction to the linespace density
    yy_pred = yy_pred.reshape((linespace_density, linespace_density))
    yy_sigma = yy_sigma.reshape((linespace_density, linespace_density))

    print("plotting data and predictions")
    # plot the original data as a scatter plot
    plot_scatter(theta_phi[:,0], theta_phi[:,1], avg_csi_mag, title=header,
                    save_filename=latest_file, filename_suffix="_original_data", show=False)
    
    # plot as a surface
    plot_figure_surface_gp(xx, yy, yy_pred, title=header, save_filename=latest_file, show=False)

    # plot the error as a heatmap
    plot_heatmap_gp(xx, yy, yy_sigma, title=header, save_filename=latest_file, filename_suffix="_mse", show=False)
    # plot as a heatmap (2D)
    plot_heatmap_gp(xx, yy, yy_pred, title=header, save_filename=latest_file, show=True)

    # print original data
    # print("plotting original data")
    # fig = go.Figure(data=[go.Scatter3d(x=theta_phi[:,0], y=theta_phi[:,1], z=avg_csi_mag, mode='markers')])
    # fig.update_layout(title='Original Beamscan Data',
    #                     autosize=True,
    #                     )
    # fig.show()
    

    print("done")
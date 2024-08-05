# experimental work discontinued

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.cm as cm

def sample_theta_phi(theta_min=0, theta_max=45, phi_min=0, phi_max=359, num_samples=1000):
    # Convert theta range to radians
    theta_min_rad = np.deg2rad(theta_min)
    theta_max_rad = np.deg2rad(theta_max)
    
    # Sample theta according to sin(theta) distribution
    u = np.random.uniform(np.sin(theta_min_rad), np.sin(theta_max_rad), num_samples)
    theta_samples = np.arcsin(u) * 180 / np.pi  # Convert back to degrees
    
    # Sample phi uniformly
    phi_samples = np.random.uniform(phi_min, phi_max, num_samples)
    
    return theta_samples, phi_samples

def average_angular_distance(theta_samples, phi_samples):
    n = len(theta_samples)
    total_distance = 0
    max_distance = 0
    min_distance = 180
    for i in range(n):
        for j in range(i+1, n):
            theta1, phi1 = np.deg2rad(theta_samples[i]), np.deg2rad(phi_samples[i])
            theta2, phi2 = np.deg2rad(theta_samples[j]), np.deg2rad(phi_samples[j])
            dtheta = theta2 - theta1
            dphi = phi2 - phi1
            # Great-circle distance formula
            a = np.sin(dtheta / 2)**2 + np.cos(theta1) * np.cos(theta2) * np.sin(dphi / 2)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
            total_distance += c
            max_distance = max(max_distance, np.rad2deg(c))
            min_distance = min(min_distance, np.rad2deg(c))
    avg_distance = total_distance / (n * (n - 1) / 2)
    avg_distance = np.rad2deg(avg_distance)# Convert to degrees
    return avg_distance, max_distance, min_distance 

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

# Parameters
theta_min = 0
theta_max = 45 #45
phi_min = 0
phi_max = 359 #359
num_samples = 1000

# Generate samples
theta_samples, phi_samples = sample_theta_phi(theta_min, theta_max, phi_min, phi_max, num_samples)

# Calculate and print the average angular distance
avg_distance,max_distance,min_distance = average_angular_distance(theta_samples, phi_samples)
print(f"Number of points: {num_samples}")
print("Sample points (theta, phi):")
for i in range(10):
    print(f"({theta_samples[i]}, {phi_samples[i]})")

print(f"Average angular distance between points: {avg_distance:.2f} degrees")
# print(f"Maximum angular distance between points: {max_distance:.2f} degrees")
# print(f"Minimum angular distance between points: {min_distance:.2f} degrees")

# Plot the samples
plot_theta_phi(theta_samples, phi_samples)


# =================================================================================== OLD CODE FROM GEN1
# def half_fibonacci_sphere(num_points):
#     """
#     Generate points on a half sphere using the half fibonacci algorithm
#     """
#     points = []
#     phi = (1 + 5 ** 0.5) / 2 - 1 # golden ratio
#     for i in range(num_points):
#         theta = 2 * i / num_points
#         points.append((theta, phi))

#     return points

# def fibonacci_sphere_arc(num_samples:int=1000, theta_range:list=(0, 45), phi_range:list=(0, 359)):
#     """
#     Generate points on an arc sphere using the fibonacci algorithm
#     """
#     points = []
#     g_ratio = np.pi * (3 - np.sqrt(5)) # golden ratio (radians)

#     # convert limits to radians
#     theta_min_rad,theta_max_rad = np.deg2rad(theta_range[0]), np.deg2rad(theta_range[1])
#     phi_min_rad,phi_max_rad = np.deg2rad(phi_range[0]), np.deg2rad(phi_range[1])

#     # Scale the number of samples to the arc area
#     total_surface_area = 2 * np.pi * (np.cos(theta_min_rad) - np.cos(theta_max_rad)) # total surface area of the sphere
#     arc_surface_area = (phi_max_rad - phi_min_rad) * (np.cos(theta_min_rad) - np.cos(theta_max_rad)) # surface area of the arc
#     adjusted_samples = int(num_samples * (arc_surface_area / total_surface_area)) # scale the number of samples to the arc area

#     for i in range(adjusted_samples):
#         y = 1 - (i / float(adjusted_samples - 1)) * 2
#         radius = np.sqrt(1 - y * y)
#         phi = (i % adjusted_samples) * g_ratio
#         x = np.cos(phi) * radius
#         z = np.sin(phi) * radius
#         theta = np.arccos(y)
#         points.append((np.rad2deg(theta), np.rad2deg(phi)))
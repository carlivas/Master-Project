import numpy as np
import matplotlib.pyplot as plt
import copy
from numba import njit, prange
from scipy.interpolate import RegularGridInterpolator
from scipy.stats import gaussian_kde
from scipy.spatial import KDTree
from mpl_toolkits.axes_grid1 import make_axes_locatable

SQRT2 = np.sqrt(2)
PI = np.pi
SQRTPI = np.sqrt(PI)


@njit
def W(x, y, hSq):
    rSq = x**2 + y**2
    w = 1/(2 * PI * hSq) * np.exp(-rSq / (2 * hSq))
    return w


@njit
def getPairwiseSeparations(ri, rj):
    M = ri.shape[0]
    N = rj.shape[0]

    dx = np.empty((M, N))
    dy = np.empty((M, N))

    for i in prange(M):
        for j in prange(N):
            dx[i, j] = ri[i, 0] - rj[j, 0]
            dy[i, j] = ri[i, 1] - rj[j, 1]

    return dx, dy


@njit(parallel=True)
def getDensity(r, pos, m, hSq):
    M = r.shape[0]
    N = pos.shape[0]

    dx, dy = getPairwiseSeparations(r, pos)

    rho = np.zeros((M, 1))
    for i in prange(M):
        for j in prange(N):
            rho[i] += m[j] * W(dx[i, j], dy[i, j], hSq)
    return rho


class DensityFieldSPH:
    def __init__(self, half_width, half_height, check_radius, resolution, simulation=None):
        print('DensityFieldSPH: DensityField is using smoothed particle hydrodynamics density estimation.')
        dx = 1 / resolution
        dy = 1 / resolution
        xx = np.linspace(-half_width + dx/2,
                         half_width - dx/2, resolution)
        yy = np.linspace(-half_height + dy/2,
                         half_height - dy/2, resolution)
        X, Y = np.meshgrid(xx, yy)

        self.resolution = resolution
        self.grid_points = np.vstack([X.ravel(), Y.ravel()]).T
        self.KDTree = KDTree(self.grid_points)

        self.bandwidthSq = check_radius**2
        self.values = np.zeros_like(self.grid_points)

        self.simulation = simulation

    def query(self, pos):
        # Find the nearest neighbors using KDTree
        dist, idx = self.KDTree.query(pos)
        return self.values[idx]

    def update(self, state):
        positions = state['pos']
        areas = state['area']
        self.values = getDensity(
            self.grid_points, positions, areas, self.bandwidthSq)

    def plot(self, size=2, title='Density field', fig=None, ax=None, vmin=0, vmax=None, extent=[-0.5, 0.5, -0.5, 0.5], colorbar=True):
        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=(size, size))
        im = ax.imshow(self.get_values().reshape(self.resolution, self.resolution), origin='lower', cmap='Greys',
                       vmin=vmin, vmax=vmax, extent=extent)
        ax.set_title(title, fontsize=7)
        if colorbar:
            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="5%", pad=0.05)
            cbar = plt.colorbar(im, cax=cax)
            cbar.set_label('Density')
        # ax.set_xticks([])
        # ax.set_yticks([])
        return fig, ax

    def get_values(self):
        return copy.deepcopy(self.values)

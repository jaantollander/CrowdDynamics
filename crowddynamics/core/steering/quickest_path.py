"""Navigation/path-planning algorithms

Continuos shortest path problem

Eikonal equation solvers

- Fast Marching Method [scikit-fmm]
- Fast Iterative Method [SCI-Solver_Eikonal]

References:
    .. [scikit-fmm] https://github.com/scikit-fmm/scikit-fmm
    .. [SCI-Solver_Eikonal] https://github.com/SCIInstitute/SCI-Solver_Eikonal

Attributes:
    MeshGrid (namedtuple):
        - values: Tuple (X, Y) of ndarrays of shape (n, m).
        - shape:
        - step: 
        - bounds:
        - indicer:
    DistanceMap:
        Ndarray of shape (n, m) where the values indicate the shortest distance
        from target.
    DirectionMap:
        Tuple (U, V) of ndarray of shape (n, m), where the value are x and y
        components of a (unit)vector field.
"""
from collections import namedtuple
from typing import Tuple, Optional

import numpy as np
import skfmm
from loggingtools.log_with import log_with
from scipy.interpolate import NearestNDInterpolator
from shapely.geometry.base import BaseGeometry
from skimage.segmentation import find_boundaries

from crowddynamics.core.geometry import geom_to_skimage

MeshGrid = namedtuple('MeshGrid', 'values shape step bounds indicer')
DistanceMap = np.ma.MaskedArray
DirectionMap = Tuple[np.ma.MaskedArray, np.ma.MaskedArray]


# Grid

@log_with(arguments=False, timed=True)
def meshgrid(step: float, minx: float, miny: float,
             maxx: float, maxy: float) -> MeshGrid:
    """2-Dimensional meshgrid with inclusive end points maxx and maxy

    Args:
        step (float): 
        minx (float): 
        miny (float): 
        maxx (float): 
        maxy (float):

    Returns:
        MeshGrid: 
    """
    x = np.arange(minx, maxx + step, step=step)
    y = np.arange(miny, maxy + step, step=step)
    values = np.meshgrid(x, y, indexing='xy')
    shape = values[0].shape

    def indicer(position):
        """Converts positions to meshgrid indices"""
        shifted = np.asarray(position) - np.array((minx, miny))
        return (shifted / step).astype(np.int64)

    return MeshGrid(
        values=values, shape=shape, step=step, bounds=(minx, miny, maxx, maxy),
        indicer=indicer
    )


@log_with(arguments=False, timed=True)
def values_to_grid(geom: BaseGeometry, grid, indicer, value: float):
    """Set values on discrete grid using scikit-image

    Args:
        geom (BaseGeometry):
            Shapely shape
        
        grid (np.ndarray):
            Grid to set values
            
        indicer (Callable): 
            Function that converts points to indices of a discrete grid. 

        value (float):
            Value to set to the grid points
    """
    for x, y in geom_to_skimage(geom, indicer):
        grid[y, x] = value


# Maps

@log_with(arguments=False, timed=True)
def distance_map(mgrid: MeshGrid,
                 targets: BaseGeometry,
                 obstacles: Optional[BaseGeometry]) -> DistanceMap:
    r"""Distance map

    Distance map :math:`S(\mathbf{x})` is obtained by solving *Eikonal equation*
    using fast marching *Fast Marching Method (FMM)* (``scikit-fmm``).

    .. math::
       \left \| \nabla S(\mathbf{x}) \right \| = \frac{1}{f(\mathbf{x})}, \quad \mathbf{x} \in \Omega

    where

    - Function :math:`f : \bar{\Omega} \mapsto (0, +\infty)` is the speed of
      travel at :math:`\mathbf{x}`

    Boundary conditions for the distance map

    .. math::
       \begin{cases}
       S(\mathbf{x}) = 0, & \mathbf{x} \in \mathcal{E} \\
       S(\mathbf{x}) \to \infty, & \mathbf{x} \in \mathcal{O}
       \end{cases}

    Initial values for speed

    .. math::
       \begin{cases}
       f(\mathbf{x}) = 1, & \mathbf{x} \in \Omega \setminus \mathcal{O} \\
       f(\mathbf{x}) \to 0, & \mathbf{x} \in \mathcal{O}
       \end{cases}

    Args:
        mgrid (MeshGrid):

        obstacles (BaseGeometry, optional):
            Impassable regions :math:`\mathcal{O}` in the domain.

        targets (BaseGeometry, optional):
            Target regions :math:`\mathcal{E}` in the domain.

    Return:
        (numpy.ndarray, numpy.ndarray, numpy.ma.MaskedArray):
            List of
            - ``mgrid``
            - ``dmap``
            - ``phi``
    """
    # Numerical values for objects in the domain
    empty_region = -1.0
    target_region = 1.0
    obstacle_region = True
    non_obstacle_region = False

    # Contour used for solving distance map
    # Mask for masked values that represent obstacles for the solver
    contour = np.full(mgrid.shape, empty_region, dtype=np.float64)
    mask = np.full(mgrid.shape, non_obstacle_region, dtype=np.bool_)

    values_to_grid(targets, contour, mgrid.indicer, target_region)
    if obstacles is not None:
        values_to_grid(obstacles, mask, mgrid.indicer, obstacle_region)

    # Solve distance map using Fast-Marching Method (FMM)
    phi = np.ma.MaskedArray(contour, mask)
    dmap = skfmm.distance(phi, dx=mgrid.step)

    return dmap


def travel_time_map():
    r"""
    Dynamics potential takes into account the positions of the agents in the
    field. Equation

    .. math::
       \left \| \nabla T(\mathbf{x}) \right \| = \frac{1}{f(\mathbf{x})}, \quad \mathbf{x} \in \Omega

    and boundary conditions

    .. math::
       f(\mathbf{x}) &= 1, \quad \mathbf{x} \in \Omega \setminus (\mathcal{O} \cup \mathcal{A}) \\
       f(\mathbf{x}) &\leq 1, \quad \mathbf{x} \in \mathcal{A} \\
       f(\mathbf{x}) &\to 0, \quad \mathbf{x} \in \mathcal{O}

    .. math::
       \frac{1}{f(\mathbf{x})} = 1 + \max \left( 0, c_{0} \left( 1 + c_{1} \frac{\mathbf{v} \cdot \nabla S(\mathbf{x})}{v_{0} \| \nabla S(\mathbf{x}) \|} \right) \right)

    - :math:`c_{0} > 0` general impact strength
    - :math:`c_{1} > 0` impact of the moving direction of an agent
    """
    return NotImplementedError


@log_with(arguments=False, timed=True)
def direction_map(dmap: DistanceMap) -> DirectionMap:
    r"""Normalized gradient of distance map.

    Direction map is not defined when length of the gradient is zero.

    .. math::
       \hat{\mathbf{e}}_{S} = -\frac{\nabla S(\mathbf{x})}{\| \nabla S(\mathbf{x}) \|}

    Args:
        dmap (numpy.ndarray):
            Distance map.

    Returns:
        numpy.ndarray:
            Direction map. Array of shape: ``dmap.shape + (2,)``
    """
    u, v = np.gradient(dmap)
    l = np.hypot(u, v)
    l[l == 0] = np.nan  # Avoids zero division
    # Flip order from (row, col) to (x, y)
    return v / l, u / l


# Potentials

@log_with(arguments=False, timed=True)
def fill_missing(mask, mgrid: MeshGrid, dir_map: DirectionMap):
    """Fill missing value with by interpolating the values from nearest neighbours

    Args:
        mgrid:
        dir_map:

    Returns:
        DirectionMap:
    """
    x, y = mgrid.values
    u, v = dir_map

    # Construct the interpolators from the boundary values surrounding the
    # missing values
    boundaries = find_boundaries(u.mask, mode='outer')
    points = np.stack((y[boundaries], x[boundaries])).T
    ip_u = NearestNDInterpolator(points, u[boundaries], rescale=False)
    ip_v = NearestNDInterpolator(points, v[boundaries], rescale=False)

    # interpolate only missing values (u.mask)
    mask2 = np.logical_xor(mask, u.mask)
    missing = (y[mask2], x[mask2])
    u[mask2] = ip_u(missing)
    v[mask2] = ip_v(missing)


def direction_map_targets(mgrid, domain, targets, obstacles, buffer_radius):
    """Vector field guiding towards targets """
    obstacles_buffered = obstacles.buffer(buffer_radius).intersection(domain)

    dmap_targets = distance_map(mgrid, targets, obstacles_buffered)
    dir_map_targets = direction_map(dmap_targets)

    # Fill values between buffered region and obstacles
    mask = np.full(mgrid.shape, False, dtype=np.bool_)
    values_to_grid(obstacles, mask, mgrid.indicer, True)
    fill_missing(mask, mgrid, dir_map_targets)

    return dir_map_targets, dmap_targets
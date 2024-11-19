import copy
from typing import *
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import KDTree
from matplotlib.colors import Normalize
from scipy.stats import gaussian_kde

from mods.plant import Plant
from mods.fields import DensityField
from mods.buffers import DataBuffer, FieldBuffer, StateBuffer


def check_pos_collision(pos: np.ndarray, plant: Plant) -> bool:
    """
    Check if a position collides with a plant.

    Parameters:
    pos (np.ndarray): The position to check.
    plant (Plant): The plant to check against.

    Returns:
    bool: True if there is a collision, False otherwise.
    """
    return np.sum((pos - plant.pos) ** 2) < plant.r ** 2


def check_collision(p1: Plant, p2: Plant) -> bool:
    """
    Check if two plants collide.

    Parameters:
    p1 (Plant): The first plant.
    p2 (Plant): The second plant.

    Returns:
    bool: True if there is a collision, False otherwise.
    """
    return np.sum((p1.pos - p2.pos) ** 2) < (p1.r + p2.r) ** 2


def dbh_to_crown_radius(dbh: float) -> float:
    """
    Empirically based quadratic regression to convert diameter at breast height (DBH) to crown radius.

    Parameters:
    dbh (float): Diameter at breast height in meters.

    Returns:
    float: Crown radius in meters.
    """
    # everything in m
    d = 1.42 + 28.17*dbh - 11.26*dbh**2
    return d/2


class Simulation:
    """
    A class to represent a simulation of plant growth and interactions.
    """

    def __init__(self, **kwargs):
        """
        Initialize a Simulation object with given parameters.

        Parameters:
        -----------
        kwargs : dict
            A dictionary of keyword arguments for simulation parameters, including:
            - land_quality (float): The quality of the land in the simulation.
            - half_width (float): Half the width of the simulation area.
            - half_height (float, optional): Half the height of the simulation area. Defaults to half_width.
            - kt_leafsize (int): The leaf size for the KDTree.
            - state_buffer_size (int, optional): The size of the state buffer. Defaults to 20.
            - state_buffer_skip (int, optional): The skip interval for the state buffer. Defaults to 1.
            - state_buffer_preset_times (list, optional): Preset times for the state buffer. Defaults to None.
            - n_iter (int): The number of iterations for the data buffer.
            - density_check_radius (float): The radius for density checks.
            - density_field_resolution (int): The resolution of the density field.
            - density_field_buffer_size (int): The size of the density field buffer.
            - density_field_buffer_skip (int, optional): The skip interval for the density field buffer. Defaults to 1.
            - density_field_buffer_preset_times (list, optional): Preset times for the density field buffer. Defaults to None.
        """
        self.kwargs = kwargs

        self.t = 0
        self.state = []
        self.biomass = None
        self.population = None
        self.land_quality = kwargs.get('land_quality')

        self.half_width = kwargs.get('half_width')
        self.half_height = kwargs.get('half_height', self.half_width)
        self.kt_leafsize = kwargs.get('kt_leafsize')
        self.kt = None

        self.state_buffer = StateBuffer(
            size=kwargs.get('state_buffer_size', 20),
            skip=kwargs.get('state_buffer_skip', 1),
            preset_times=kwargs.get('state_buffer_preset_times', None)
        )

        self.data_buffer = DataBuffer(
            size=kwargs.get('n_iter'),
        )

        # density_field_resolution = np.ceil((2*self.half_width) /
        #                                    (np.sqrt(2) * kwargs.get('density_check_radius'))).astype(int)
        # density_field_resolution = max(25, density_field_resolution)
        # print(f'Simulation.__init__(): {density_field_resolution=}')
        self.density_field = DensityField(
            half_width=self.half_width,
            half_height=self.half_height,
            check_radius=kwargs.get('density_check_radius'),
            resolution=kwargs.get('density_field_resolution'),
            simulation=self
        )

        self.density_field_buffer = FieldBuffer(
            sim=self,
            resolution=kwargs.get('density_field_resolution'),
            size=kwargs.get('density_field_buffer_size'),
            skip=kwargs.get('density_field_buffer_skip', 1),
            preset_times=kwargs.get('density_field_buffer_preset_times', None)
        )

    def add(self, plant: Union[Plant, List[Plant], np.ndarray]) -> None:
        """
        Add a plant or a list of plants to the simulation.

        Parameters:
        -----------
        plant : Union[Plant, List[Plant], np.ndarray]
            A Plant object, a list of Plant objects, or a numpy array of Plant objects to be added to the simulation.

        Raises:
        -------
        ValueError:
            If the input is not a Plant object or an array_like of Plant objects.
        """
        if isinstance(plant, Plant):
            self.state.append(plant)
        elif isinstance(plant, (list, np.ndarray)):
            for p in plant:
                if isinstance(p, Plant):
                    self.state.append(p)
                else:
                    raise ValueError(
                        "All elements in the array must be Plant objects")
        else:
            raise ValueError(
                "Input must be a Plant object or an array_like of Plant objects")

    def update_kdtree(self) -> None:
        """
        Update the KDTree with the current plant positions.

        If there are no plants in the simulation, the KDTree is set to None.
        Otherwise, the KDTree is updated with the positions of the plants.
        """
        if len(self.state) == 0:
            self.kt = None
        else:
            self.kt = KDTree(
                [plant.pos for plant in self.state], leafsize=self.kt_leafsize)

    def step(self) -> None:
        """
        Perform a single time step of the simulation.

        This method updates all plants, collects non-dead plants, updates necessary data structures,
        and saves the state and density field at specified intervals.
        """

        # First Phase: Update all plants
        for plant in self.state:
            plant.update(self)

        # Second Phase: Collect non-dead plants and add them to the new state, and make sure all new plants get a unique id
        new_plants = []
        plant_ids = [plant.id for plant in self.state]

        for plant in self.state:
            if not plant.is_dead:
                if plant.id is None:
                    plant.id = max(
                        [id for id in plant_ids if id is not None]) + 1
                new_plants.append(plant)

        self.state = new_plants

        self.t += 1

        # Update necessary data structures
        self.update_kdtree()
        self.density_field.update()

        data = self.data_buffer.analyze_and_add(self.get_state(), t=self.t)
        self.biomass = data[0]
        self.population = data[1]

        do_save_state = self.t % self.state_buffer.skip == 0 or self.t in self.state_buffer.preset_times
        do_save_density_field = self.t % self.density_field_buffer.skip == 0 or self.t in self.density_field_buffer.preset_times

        if do_save_state:
            self.state_buffer.add(state=self.get_state(), t=self.t)
        if do_save_density_field:
            self.density_field_buffer.add(
                field=self.density_field.get_values(), t=self.t)

    def run(self, n_iter: Optional[int] = None) -> None:
        """
        Run the simulation for a given number of iterations.

        Parameters:
        -----------
        n_iter : Optional[int]
            The number of iterations to run the simulation. If None, the value from kwargs is used.
        """
        import time
        if n_iter is None:
            n_iter = self.kwargs.get('n_iter')
        start_time = time.time()
        try:
            for _ in range(1, n_iter):
                self.step()

                # if no plants are left or if the number of plants exceeds 100 times the number of plants in the initial state, stop the simulation
                l = len(self.state)
                if l == 0 or l > self.kwargs.get('num_plants') * 100:
                    break

                elapsed_time = time.time() - start_time

                if _ % 3 == 0:
                    dots = '.  '
                elif _ % 3 == 1:
                    dots = '.. '
                else:
                    dots = '...'

                print(f'{dots} Elapsed time: {elapsed_time:.2f}s', end='\r')

        except KeyboardInterrupt:
            print('\nInterrupted by user...')

    def get_collisions(self, plant: Plant) -> List[Plant]:
        """
        Get a list of plants that collide with the given plant.

        Parameters:
        -----------
        plant : Plant
            The plant to check for collisions.

        Returns:
        --------
        List[Plant]
            A list of plants that collide with the given plant.
        """
        plant.is_colliding = False
        collisions = []
        if self.kt is not None:
            indices = self.kt.query_ball_point(
                x=plant.pos, r=plant.d, workers=-1)
            for i in indices:
                other_plant = self.state[i]
                if other_plant != plant:
                    if check_collision(plant, other_plant):
                        plant.is_colliding = True
                        other_plant.is_colliding = True
                        collisions.append(other_plant)
        return collisions

    def quality_nearby(self, pos: np.ndarray) -> float:
        """
        Get the quality of the land near a given position.

        Parameters:
        -----------
        pos : np.ndarray
            The position to check.

        Returns:
        --------
        float
            The quality of the land near the given position.
        """
        quality = self.land_quality
        pos_in_box = np.abs(pos[0]) < self.half_width and np.abs(
            pos[1]) < self.half_height
        if pos_in_box:
            density_nearby = self.density_field.query(pos)
            quality = density_nearby + self.land_quality
        return quality

    def get_state(self):
        return copy.deepcopy(self.state)

    def get_density_field(self):
        return copy.deepcopy(self.density_field)

    def initiate(self) -> None:
        """
        Initialize the simulation by updating necessary data structures.

        This method updates the KDTree, density field, and buffers with the initial state of the simulation.
        """
        self.update_kdtree()
        self.density_field.update()

        data = self.data_buffer.analyze_and_add(state=self.get_state(), t=0)
        self.biomass = data[0]
        self.population = data[1]
        self.state_buffer.add(state=self.get_state(), t=0)
        self.density_field_buffer.add(
            field=self.density_field.get_values(), t=0)

    def initiate_uniform_lifetimes(self, n: int, t_min: float, t_max: float, **plant_kwargs: Any) -> None:
        """
        Initialize the simulation with plants having uniform lifetimes. This is only valid for the case where the growth rate is constant.

        Parameters:
        -----------
        n : int
            The number of plants to initialize.
        t_min : float
            The minimum lifetime of the plants.
        t_max : float
            The maximum lifetime of the plants.
        plant_kwargs : dict
            Additional keyword arguments for the Plant objects.
        """
        growth_rate = plant_kwargs['growth_rate']
        plant_kwargs['r_max'] = t_max * growth_rate
        plants = [
            Plant(
                pos=np.random.uniform(-self.half_width, self.half_width, 2),
                r=np.random.uniform(t_min, t_max) * growth_rate, id=i,
                **plant_kwargs
            )
            for i in range(n)
        ]
        self.add(plants)
        self.initiate()

    def initiate_dense_distribution(self, n: int, **plant_kwargs: Any) -> None:
        """
        Initialize the simulation with a dense distribution of plants. The distribution is based on empirical data taken from Cummings et al. (2002).

        Parameters:
        -----------
        n : int
            The number of plants to initialize.
        plant_kwargs : dict
            Additional keyword arguments for the Plant objects.
        """
        _m = self.kwargs.get('_m')
        mean_dbhs = np.array([0.05, 0.2, 0.4, 0.6, 0.85, 1.50])  # in m
        mean_rs = dbh_to_crown_radius(mean_dbhs) * _m
        freqs = np.array([5800, 378.8, 50.98, 13.42, 5.62, 0.73])

        # Apply log transformation to the data
        log_mean_rs = np.log(mean_rs)

        # Calculate the KDE of the log-transformed data
        kde = gaussian_kde(log_mean_rs, weights=freqs, bw_method='silverman')

        # Resample from the KDE and transform back to the original space
        log_samples = kde.resample(n)[0]
        samples = np.exp(log_samples)

        # Create the plants
        plants = [
            Plant(
                pos=np.random.uniform(-self.half_width, self.half_width, 2),
                r=r, id=i, **plant_kwargs
            )
            for i, r in enumerate(samples)
        ]
        self.add(plants)
        self.initiate()

    def plot_state(self, state: List[Plant], t: Optional[int] = None, size: int = 2, fig: Optional[plt.Figure] = None, ax: Optional[plt.Axes] = None, highlight: Optional[List[int]] = None) -> Tuple[plt.Figure, plt.Axes]:
        """
        Plot a simulation state.

        Parameters:
        -----------
        state : List[Plant]
            The state of the simulation to plot. This parameter is required.
        t : Optional[int]
            The time step to display in the plot title. Defaults to None.
        size : int
            The size of the plot. Defaults to 2.
        fig : Optional[plt.Figure]
            The figure to plot on. If None, a new figure is created. Defaults to None.
        ax : Optional[plt.Axes]
            The axes to plot on. If None, new axes are created. Defaults to None.
        highlight : Optional[List[int]]
            A list of plant IDs to highlight in the plot. Defaults to None.

        Returns:
        --------
        Tuple[plt.Figure, plt.Axes]
            The figure and axes of the plot.
        """
        if ax is None:
            fig, ax = plt.subplots(1, 1, figsize=(size, size))
        ax.set_xlim(-self.half_width, self.half_width)
        ax.set_ylim(-self.half_height, self.half_height)
        ax.set_aspect('equal', 'box')
        if t is not None:
            ax.set_title(f'{t=}', fontsize=7)
        else:
            ax.set_title('')
        for plant in state:
            if highlight is not None and plant.id in highlight:
                color = 'red'
            else:
                color = 'green'
            density = self.density_field.query(plant.pos)
            ax.add_artist(plt.Circle(plant.pos, plant.r,
                          color=color, fill=True, transform=ax.transData))

            sm = plt.cm.ScalarMappable(norm=Normalize(
                vmin=0, vmax=self.density_field.get_values().max()), cmap='Greys')
            color = sm.to_rgba(density)
            ax.add_artist(plt.Circle(plant.pos, plant.r, fill=True,
                          color=color, alpha=1, transform=ax.transData))

        _m = self.kwargs.get('_m')
        x_ticks = ax.get_xticks() * _m
        y_ticks = ax.get_yticks() * _m
        ax.set_xticklabels([f'{x:.1f}' for x in x_ticks])
        ax.set_yticklabels([f'{y:.1f}' for y in y_ticks])
        return fig, ax

    def plot(self, size: int = 2, t: Optional = None, highlight: Optional[List[int]] = None) -> Tuple[plt.Figure, plt.Axes]:
        """
        Plot the current state of the simulation.

        Parameters:
        -----------
        size : int
            The size of the plot. Defaults to 2.
        t : int
            The time step to display in the plot title. Defaults to self.t.
        highlight : Optional[List[int]]
            A list of plant IDs to highlight in the plot. Defaults to None.

        Returns:
        --------
        Tuple[plt.Figure, plt.Axes]
            The figure and axes of the plot.
        """
        if t is None:
            t = self.t
        fig, ax = self.plot_state(
            self.get_state(), t=t, size=size, highlight=highlight)
        return fig, ax

    def plot_states(self, states: List[List[Plant]], times: Optional[List[int]] = None, size: int = 2) -> Tuple[plt.Figure, plt.Axes]:
        """
        Plot multiple states of the simulation.

        Parameters:
        -----------
        states : List[List[Plant]]
            A list of states to plot.
        times : Optional[List[int]]
            A list of time steps corresponding to the states. Defaults to None.
        size : int
            The size of the plot. Defaults to 2.

        Returns:
        --------
        Tuple[plt.Figure, plt.Axes]
            The figure and axes of the plot.
        """
        l = len(states)
        n_rows = int(np.floor(l / np.sqrt(l)))
        n_cols = (l + 1) // n_rows + (l % n_rows > 0)
        print(f'simulation.plot_states(): {n_rows=}, {n_cols=}')

        fig, ax = plt.subplots(n_rows, n_cols, figsize=(
            size * n_cols, size * n_rows))
        fig.subplots_adjust(left=0.05, bottom=0.05, right=0.95,
                            top=0.95, wspace=0.05, hspace=0.05)
        fig.tight_layout()
        if len(states) == 1:
            self.plot_state(states[0], t=times[0], size=size, ax=ax)
        else:
            i = 0
            while i < len(states):
                state = states[i]
                if n_rows == 1:
                    k = i
                    self.plot_state(
                        state=state, t=times[i], size=size, fig=fig, ax=ax[k])
                else:
                    l = i // n_cols
                    k = i % n_cols
                    self.plot_state(
                        state=state, t=times[i], size=size, fig=fig, ax=ax[l, k])
                i += 1
        if len(states) < n_rows * n_cols:
            for j in range(len(states), n_rows * n_cols):
                if n_rows == 1:
                    ax[j].axis('off')
                else:
                    l = j // n_cols
                    k = j % n_cols
                    ax[l, k].axis('off')

        return fig, ax

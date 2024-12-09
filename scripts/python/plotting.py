import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import os
import sys

from mods.plant import Plant
from mods.simulation import Simulation
from mods.buffers import DataBuffer, FieldBuffer, StateBuffer
from mods.utilities import print_nested_dict

path = sys.argv[1]
load_folder = os.path.abspath(path)
print(f'load_folder: {load_folder}')

sim_nums = [f.split('_')[-1].split('.')[0]
            for f in os.listdir(load_folder) if 'kwargs' in f][::-1]
print(f'sim_nums: {sim_nums}')

print_kwargs = bool(int(sys.argv[2]))
plot_data = bool(int(sys.argv[3]))
plot_states = bool(int(sys.argv[4]))
plot_density_field = bool(int(sys.argv[5]))

fast_plot = bool(int(sys.argv[6]))

prev_mod = 0
p = 0
for i, n in enumerate(sim_nums[:10]):
    print(f'\nplotting.py: sim {i+1} / {len(sim_nums)}')
    print(f'plotting.py: Loading sim {n}...')

    kwargs = pd.read_json(
        f'{load_folder}/kwargs_{n}.json', typ='series').to_dict()
    sim_kwargs = kwargs.get('sim_kwargs')
    plant_kwargs = kwargs.get('plant_kwargs')
    lq = sim_kwargs.get('land_quality')
    sg = plant_kwargs.get('species_germination_chance')
    dens0 = sim_kwargs.get('dens0', -1)
    dispersal_range = plant_kwargs.get('dispersal_range')
    num_plants = sim_kwargs.get('num_plants')
    # title = f'{n}   (lq={lq:.3e},   sg={sg:.3e},  dispersal_range={(dispersal_range):.3e})'
    # title = f'{n}   (lq={lq:.3e},   sg={sg:.3e},  dens0={(dens0):.3e})'
    title = f'{n}   (dens0={(dens0):.3e})'

    if print_kwargs:
        print('plotting.py: Loaded kwargs, now printing...')
        print_nested_dict(kwargs)
        print()

    if plot_data:
        data_buffer_arr = pd.read_csv(
            f'{load_folder}/data_buffer_{n}.csv')
        data_buffer = DataBuffer(data=data_buffer_arr)
        print('plotting.py: Loaded data_buffer, now plotting...')
        data_buffer.plot(title=title)

    if plot_states:
        state_buffer_arr = pd.read_csv(
            f'{load_folder}/state_buffer_{n}.csv', header=None)
        state_buffer = StateBuffer(
            data=state_buffer_arr, plant_kwargs=plant_kwargs)
        print('plotting.py: Loaded state_buffer, now plotting...')
        state_buffer.plot(size=2, title=title, fast=fast_plot)

    if plot_density_field:
        density_field_buffer_arr = pd.read_csv(
            f'{load_folder}/density_field_buffer_{n}.csv', header=None)
        density_field_buffer = FieldBuffer(
            data=density_field_buffer_arr)
        print('plotting.py: Loaded density_field_buffer, now plotting...')

        density_field_buffer.plot(
            size=2, title=title)

    p += int(plot_data) + \
        int(plot_states) + int(plot_density_field)
    mod = p % 8
    if mod < prev_mod or i >= len(sim_nums) - 1:
        plt.show()

    prev_mod = mod

print('plotting.py: Done.\n')

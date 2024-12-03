import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import os

from mods.plant import Plant
from mods.simulation import Simulation
from mods.buffers import DataBuffer, FieldBuffer, StateBuffer
n_iter = 150
_m = 1/3000
sim_kwargs = {
    'land_quality': 5000e-5,
    '_m': _m,
    'n_iter': n_iter,
    'buffer_skip': 10,
}
plant_kwargs = {
    'growth_rate': 0.1 * _m,
    'r_min': 0.01 * _m,
    'r_max': 30 * _m,
    'species_germination_chance': 4000e-5,
    'dispersal_range': 90 * _m,
}
sim = Simulation(**sim_kwargs)
sim.initiate_uniform_lifetimes(n=100, t_min=0, t_max=100, **plant_kwargs)

sim.run()

sim.state_buffer.plot()
plt.show()
# load_folder = r'Data\data_buff_test'
# sim_nums = [f.split('_')[-1].split('.')[0]
#             for f in os.listdir(load_folder) if 'data_buffer' in f]  # [::-1]

# p = 0
# for i, n in enumerate(sim_nums[:1]):
#     print(f'\nplotting.py: sim {i+1} / {len(sim_nums)}')
#     print(f'plotting.py: Loading sim {n}...')

#     kwargs = pd.read_json(
#         f'{load_folder}/kwargs_{n}.json', typ='series').to_dict()
#     sim_kwargs = kwargs['sim_kwargs']
#     plant_kwargs = kwargs['plant_kwargs']
#     lq = sim_kwargs['land_quality']
#     sg = plant_kwargs['species_germination_chance']
#     print('plotting.py: Loaded kwargs...')

#     data_buffer_df = pd.read_csv(
#         f'{load_folder}/data_buffer_{n}.csv', header=0)
#     print(data_buffer_df)
#     data_buffer = DataBuffer(data=data_buffer_df)
#     print('plotting.py: Loaded data_buffer...')

# biomass, time, population = data_buffer.get_data(
#     keys=['Biomass', 'Time', 'Population'])

# fig, ax = plt.subplots(2, 1, figsize=(6, 6))
# ax[0].plot(time, biomass, label='Biomass', color='green')
# ax[1].plot(time, population, label='Population', color='blue')
# plt.show()


# # data_buffer.plot(title=f'sim {n}, lq = {lq:.3f}, sg = {sg:.3f}')
# # plt.show()

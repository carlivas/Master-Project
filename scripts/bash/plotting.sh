#!/bin/bash

# Navigate to the vscode directory
cd C:/Users/carla/Dropbox/_CARL/UNI/KANDIDAT/PROJEKT/Code || exit 1

# Activate the virtual environment
source ./scripts/bash/venv.sh

# Run the plotting script
path='Data\MODI\modi_ensemble_L4500\precipitation_6400e-5'

echo "plotting.sh: Loading from $path"
echo "plotting.sh: Please enter arguments:"

read -p "plotting.sh: Detailed plot? (might take longer...) (1/0): " detailed_plot
# Set default values
print_kwargs=1
plot_data=1
plot_states=1
plot_density_field=1
detailed_plot=${detailed_plot:-0}

converted_path=$(echo "$path" | sed 's|\\\\|/|g')

echo -ne "\n------------------------------------------------------------\n"

# Run the plotting Python script
python scripts/python/plotting.py $converted_path $print_kwargs $plot_data $plot_states $plot_density_field $detailed_plot
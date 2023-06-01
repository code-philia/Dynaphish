#!/bin/bash

# Source the Conda configuration
CONDA_BASE=$(conda info --base)
source "$CONDA_BASE/etc/profile.d/conda.sh"

# Create a new conda environment with Python 3.7
ENV_NAME="myenv"

# Check if the environment already exists
conda info --envs | grep -w "$ENV_NAME" > /dev/null

if [ $? -eq 0 ]; then
    # If the environment exists, activate it
    echo "Activating Conda environment $ENV_NAME"
    conda activate "$ENV_NAME"
else
    # If the environment doesn't exist, create it with Python 3.7 and activate it
    echo "Creating and activating new Conda environment $ENV_NAME with Python 3.7"
    conda create -n "$ENV_NAME" python=3.8
    conda activate "$ENV_NAME"
fi

# Install PhishIntention
conda activate "$ENV_NAME"
git clone https://github.com/lindsey98/PhishIntention.git
cd PhishIntention
chmod +x ./setup.sh
./setup.sh
cd ../
rm -rf PhishIntention

## Install MyXDriver
conda activate "$ENV_NAME"
git clone https://github.com/lindsey98/MyXdriver_pub.git
cd MyXdriver_pub
chmod +x ./setup.sh
./setup.sh
cd ../
rm -rf MyXdriver_pub

conda activate "$ENV_NAME"
pip install -r requirements.txt
echo "All packages installed successfully!"


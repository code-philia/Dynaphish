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
    conda create -n "$ENV_NAME" python=3.7
    conda activate "$ENV_NAME"
fi

mkl_path=$(conda info --base)/envs/"$ENV_NAME"/lib
echo "MKL path is $mkl_path"
# Export the LD_LIBRARY_PATH environment variable
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$mkl_path"

# Get the CUDA and cuDNN versions, install pytorch, torchvision
pip install -r requirements.txt
conda install typing_extensions
cuda_version=$(nvcc --version | grep release | awk '{print $6}' | cut -c2- | awk -F. '{print $1"."$2}')
pip install torch==1.8.1 torchvision -f "https://download.pytorch.org/whl/cu${cuda_version//.}/torch_stable.html"

# Install Detectron2
cuda_version=$(nvcc --version | grep release | awk '{print $6}' | cut -c2- | awk -F. '{print $1$2}')
case $cuda_version in
    "111" | "102" | "101")
      python -m pip install detectron2 -f \
  https://dl.fbaipublicfiles.com/detectron2/wheels/cu"$cuda_version"/torch1.8/index.html
    ;;
    *)
      echo "Please build Detectron2 from source https://detectron2.readthedocs.io/en/latest/tutorials/install.html">&2
      exit 1
      ;;
esac

## Install MMOCR
## Install MMOCR dependencies
conda install -c conda-forge openpyxl -y
pip install mmcv-full=="1.3.8" -f "https://download.openmmlab.com/mmcv/dist/cu${cuda_version//.}/torch$(python -c "import torch; print(torch.__version__[:5])")/index.html"
pip install -U mmocr

## Install MyXDriver
cd ../
pwd
git clone https://github.com/lindsey98/MyXdriver_pub.git
cd MyXdriver_pub

# Check if the setup.sh file exists
if [ -f "setup.sh" ]; then
    # Make the setup.sh file executable
    chmod +x setup.sh
    # Run the setup.sh file
    ./setup.sh
else
    echo "Error: setup.sh not found in the repository"
    exit 1
fi
# download xdriver model
file_id="1ouhn17V2ylzKnLIbrP-IpV7Rl7pmHtW-"
output_file="model_final.pth"
cd xutils/forms/button_locator_models/
wget --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id='$file_id -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=$file_id" -O "$output_file" && rm -rf /tmp/cookies.txt


# Install PhishIntention
export LD_LIBRARY_PATH=""
pip install git+https://github.com/lindsey98/PhishIntention.git
package_location=$(pip show phishintention | grep Location | awk '{print $2}')

if [ -z "PhishIntention" ]; then
  echo "Package PhishIntention not found in the Conda environment myenv."
  exit 1
else
  echo "Going to the directory of package PhishIntention in Conda environment myenv."
  cd "$package_location/phishintention" || exit
  pwd
  # download models and unzip
  file_id="1zw2MViLSZRemrEsn2G-UzHRTPTfZpaEd"
  output_file="src.zip"
  # Download the file using wget
  wget --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id='$file_id -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=$file_id" -O "$output_file" && rm -rf /tmp/cookies.txt
  dir_name=$(unzip -l src.zip | awk '/^[^ ]/ {print $4}' | awk -F'/' '{print $1}' | uniq)
  echo $dir_name
  # Remove the directory if it already exists
  if [ -d "src/" ]; then
      rm -rf "src/"
  fi
  unzip -o src.zip
  rm src.zip
fi

echo "All packages installed successfully!"


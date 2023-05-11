#!/bin/bash

# Get the conda environment path
conda_env_name="myenv"
conda_base="$(conda info --base)"
conda_env_path="${conda_base}/envs/${conda_env_name}"

echo "conda_env_path: ${conda_env_path}"
pwd
# Replace the placeholder in the YAML template
sed "s|CONDA_ENV_PATH_PLACEHOLDER|$conda_env_path|g" field_study_logo2brand/configs_template.yaml > ./field_study_logo2brand/configs.yaml

## Download targetlist and domainmap
cd field_study_logo2brand
file_id="1UKykkUTr8xIIYbaAU1h245R07RyM8gIw"
output_file="expand_targetlist.zip"
wget --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id='$file_id -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=$file_id" -O "$output_file" && rm -rf /tmp/cookies.txt

file_id="1DeoI1pjkEcPWDNAO6kTlLin0UIUZfF1Y"
output_file="domain_map.pkl"
wget --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id='$file_id -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=$file_id" -O "$output_file" && rm -rf /tmp/cookies.txt

# remove previous cached files
file_path="LOGO_FEATS.npy"

if [ -f "$file_path" ]; then
    echo "File exists, deleting it..."
    rm "$file_path"
else
    echo "File does not exist."
fi

file_path="LOGO_FILES.npy"

if [ -f "$file_path" ]; then
    echo "File exists, deleting it..."
    rm "$file_path"
else
    echo "File does not exist."
fi

# DynaPhish
Official repository for "Knowledge Expansion and Counterfactual Interaction for Reference-Based Phishing Detection".
Published in USENIX Security 2023. 

## Introduction

Existing reference-based phishing detectors:
- :x: Rely on a static reference list which includes a limited number of protected brands
- :x: Unable to address logo-less phishing webpages
- :x: Publish static benchmark datasets that are unreplicable

In this work, we propose a framework called DynaPhish, as a complementary module for all reference-based phishing detectors. Our contributions lie in three folds:
- :white_check_mark: We perform on-the-fly **knowledge expansion** of the reference list in an automatic manner, ensuring the reference list's coverage
- :white_check_mark: We introduce the **behavioral intention**, which makes phishing decisions via observing the suspicious behaviors during the login action
- :white_check_mark: We publish DynaPD, which includes 6K live phishing kits that are safe and interactable. We host a sampled version [**DynaPD**](http://ec2-13-49-66-89.eu-north-1.compute.amazonaws.com/).

## Framework

<img src="./overview.png">

Dynaphish consists of the following steps:
- Step 1: Run the reference-based detector as normal.
- Step 2: If the detector cannot recognize the phishing target, run the **Brand Knowledge Expansion** module, it will take the domain or the logo from the webpage, and search for the relevant brand with Google search API and Google OCR API.
- Step 3: If a brand can be returned from the **Brand Knowledge Expansion** module, we will expand the reference list and re-run step 1.
- Step 4: If the **Brand Knowledge Expansion** fails, we will run **Web Interaction**, this will check whether the webpage exhibits any suspicious behaviors during login.
- Step 5: A phishing alarm will be raised if either the reference-based detector or the **Web Interaction** reports the webpage as phishing. 

## Project Structure
```
|_ knowledge_expansion: Knowledge Expansion Module
  |_ brand_knowledge_online.py: Knowledge Expansion Class
|_ field_study_logo2brand: testing scripts
  |_ configs_template.yaml: configuration file for the models
  |_ dynaphish_main.py: main script
```

## Setup
Requirements
- CUDA 11

Implemented and tested on Ubuntu 16.04 and 20.04, CUDA 11.1, cuDNN 10.1. 
Should work on other debian-based systems as well.

1. Install the required packages by
```
chmod +x setup.sh
./setup.sh
```
This script will create a new conda environment called **myenv**.

2. Update the configuration file for knowledge expansion module
```
chmod +x update_config.sh
./update_config.sh
```

3. Create a [google cloud service account](https://console.cloud.google.com/), setup the billing details
    - Create a project, enable "Custom Search API", "Cloud Vision API"
    - For "Custom Search API", get the API Key and Search Engine ID following this [guide](https://developers.google.com/custom-search/v1/overview).
    - Create a blank txt file in directory "knowledge_expansion/api_key.txt", copy and paste your API Key and Search Engine ID into the txt file like the following:
     ```text 
      [YOUR_API_KEY]
      [YOUR_SEARCH_ENGINE_ID]
     ```
    - For "Cloud Vision API", download the JSON key following this [guide](https://cloud.google.com/vision/docs/setup), save the JSON file under "knowledge_expansion/discoverylabel.json"

4. The main script is field_study_logo2brand/dynaphish_main.py
```
conda activate myenv
python -m field_study_logo2brand.dynaphish_main --folder [folder_to_test, e.g. datasets/test_sites] 
```

## References
If you find our work useful, please consider cite our paper
```
@inproceedings {291106,
    author = {Ruofan Liu and Yun Lin and Yifan Zhang and Penn Han Lee and Jin Song Dong},
    title = {Knowledge Expansion and Counterfactual Interaction for {Reference-Based} Phishing Detection},
    booktitle = {32nd USENIX Security Symposium (USENIX Security 23)},
    year = {2023},
    isbn = {978-1-939133-37-3},
    address = {Anaheim, CA},
    pages = {4139--4156},
    url = {https://www.usenix.org/conference/usenixsecurity23/presentation/liu-ruofan},
    publisher = {USENIX Association},
    month = aug,
}
```

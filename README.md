# DynaPhish
Official repository for "Knowledge Expansion and Counterfactual Interaction for Reference-Based Phishing Detection".
Published in USENIX Security 2023. 

<div align="center">

![Dialogues](https://img.shields.io/badge/DynaPD\_Benchmark\_Size-6K-green?style=flat-square)
![Dialogues](https://img.shields.io/badge/MyXdriver-Released-green?style=flat-square)

</div>

<p align="center">
  <a href="https://ec2-18-206-250-207.compute-1.amazonaws.com/dynapd/">DynaPD 6K Phishing Kits Online Version</a> •
  <a href="https://drive.google.com/file/d/1o2Hgr3SvtcsVsMiB4gnSafMezc_4FSLa/view?usp=sharing">DynaPD 6K Phishing Kits Source Code</a> •
  <a href="https://github.com/lindsey98/MyXdriver_pub">WebInteraction Driver: MyXdriver</a> •
  <a href="https://www.usenix.org/conference/usenixsecurity23/presentation/liu-ruofan">Paper</a> •
  <a href="https://sites.google.com/view/dynlaphish-website">Website</a> •
  <a href="#citation">Citation</a>

</p>

## Introduction

Existing reference-based phishing detectors:
- :x: Rely on a **limited reference list** which cannot adapt to temporal (e.g. emerging cryptocurrency brands) and regional (e.g. local brands) interests
- :x: Unable to address **logo-less phishing** webpages
- :x: Use **un-interactable benchmark datasets** as the test environment

In this work, we propose a framework called DynaPhish, as a complementary module for all reference-based phishing detectors. Our contributions lie in three folds:
- :white_check_mark: We perform on-the-fly **knowledge expansion** of the reference list automatically. Meanwhile, we use the **popularity-based validation** mechanism to ensure the benignity of added reference.
- :white_check_mark: We are the first to introduce the **behavioral intention**, which makes phishing decisions via observing the suspicious behaviors during the login action
- :white_check_mark: We publish **DynaPD**, which includes 6K clean and live phishing kits that are safe and interactable. Download from here: [**DynaPD**](https://drive.google.com/file/d/1o2Hgr3SvtcsVsMiB4gnSafMezc_4FSLa/view?usp=sharing). Visit the online demo here: [**DynaPD Dataset Demo**](https://ec2-18-206-250-207.compute-1.amazonaws.com/dynapd/).

## Framework

<img src="./overview.png">

Dynaphish consists of the following steps:
- Step 1: Run the reference-based detector as normal.
- Step 2: If the detector cannot recognize the phishing target, run the **Brand Knowledge Expansion** module. It will take the domain or the logo from the webpage, and search for the relevant brand with Google search API and Google OCR API.
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
Should work on other Debian-based systems as well.

1. Install the required packages by
```bash
chmod +x setup.sh
export ENV_NAME="dynaphish" && ./setup.sh
```
This script will create a new conda environment called **dynaphish**.

2. Update the configuration file for the knowledge expansion module
```bash
chmod +x update_config.sh
./update_config.sh
```

3. Create a [google cloud service account](https://console.cloud.google.com/), set the billing details
    - Create a project, enable "Custom Search API", "Cloud Vision API"
    - For "Custom Search API", get the API Key and Search Engine ID following this [guide](https://developers.google.com/custom-search/v1/overview).
    - Create a blank txt file in the directory "knowledge_expansion/api_key.txt", copy and paste your API Key and Search Engine ID into the txt file like the following:
     ```text 
      [YOUR_API_KEY]
      [YOUR_SEARCH_ENGINE_ID]
     ```
    - For "Cloud Vision API", download the JSON key following this [guide](https://cloud.google.com/vision/docs/setup), save the JSON file under "knowledge_expansion/discoverylabel.json"

4. The main script is field_study_logo2brand/dynaphish_main.py
```bash
conda activate dynaphish
python -m field_study_logo2brand.dynaphish_main --folder [folder_to_test, e.g. datasets/test_sites] 
```

## Citation
If you find our work useful, please consider citing our paper :)
```bibtex
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

## Contacts
I you encounter any issues in code deployment, please reach us via Email or create an issue in the repository: liu.ruofan16@u.nus.edu, lin_yun@sjtu.edu.cn

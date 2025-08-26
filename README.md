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

## Project Structure

We include the knowledge expansion part in this repository.

```
|_ knowledge_expansion: Knowledge Expansion Module
  |_ brand_knowledge_online.py: Knowledge Expansion Class
```

## Setup

Tested on Ubuntu, CUDA 11

1. Install the required packages by
```bash
conda create -n dynaphish python=3.10
conda activate dynaphish
pip install -r requirements.txt
pip install torch==1.11.0+cu113 torchvision==0.12.0+cu113 torchaudio==0.11.0 --extra-index-url https://download.pytorch.org/whl/cu113
pip install --no-build-isolation git+https://github.com/facebookresearch/detectron2.git
cd knowledge_expansion/phishintention
chmod +x setup.sh
./setup.sh
sudo apt install -y libxss1 libappindicator3-1 libindicator7
```

2. Create a [google cloud service account](https://console.cloud.google.com/), set the billing details
- Create a project, enable "Custom Search API", "Cloud Vision API"
- For "Custom Search API", get the API Key and Search Engine ID following this [guide](https://developers.google.com/custom-search/v1/overview).
- Create a blank txt file in the directory ``knowledge_expansion/api_key.txt``, copy and paste your API Key and Search Engine ID into the txt file like the following:
   ```text 
    [YOUR_API_KEY]
    [YOUR_SEARCH_ENGINE_ID]
   ```
- Create service account and create key follow this [guide](https://cloud.google.com/iam/docs/keys-create-delete#iam-service-account-keys-create-console), save the JSON to ``knowledge_expansion/discoverylabel.json``
    ```text
    {
      "type": "service_account",
      "project_id": "PROJECT_ID",
      "private_key_id": "KEY_ID",
      "private_key": "-----BEGIN PRIVATE KEY-----\nPRIVATE_KEY\n-----END PRIVATE KEY-----\n",
      "client_email": "SERVICE_ACCOUNT_EMAIL",
      "client_id": "CLIENT_ID",
      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
      "token_uri": "https://accounts.google.com/o/oauth2/token",
      "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
      "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/SERVICE_ACCOUNT_EMAIL"
    }
    ```

3. Knowledge expansion
```bash
conda activate dynaphish
python -m knowledge_expansion.main --folder [folder_to_test, e.g. datasets/test_sites] 
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

import tldextract
import os
import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))  # /git_space/Dynaphish

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from knowledge_expansion.brand_knowledge_online import BrandKnowledgeConstruction
import os
from PIL import Image
import numpy as np
import time
import cv2
import re
from datetime import date, timedelta
import warnings
import configs as configs
from tqdm import tqdm
import torch
import torch.nn as nn
from knowledge_expansion.phishintention.modules.awl_detector import pred_rcnn, vis, find_element_type
from knowledge_expansion.phishintention.modules.logo_matching import ocr_main, l2_norm
from knowledge_expansion.phishintention.configs import load_config
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from PIL import Image, ImageOps
from torchvision import transforms
warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.functional")
# todo: fill in your Google service account
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = configs.google_cloud_json_credentials

class LogoDetector(nn.Module):
    def __init__(self, predictor):
        super().__init__()
        self.predictor = predictor

    def forward(self, screenshot_path: str) -> np.ndarray:
        # Run detection with RCNN predictor
        pred_boxes, pred_classes, _ = pred_rcnn(
            im=screenshot_path,
            predictor=self.predictor
        )

        # Filter to "logo" class
        logo_pred_boxes, _ = find_element_type(
            pred_boxes, pred_classes, bbox_type="logo"
        )
        logo_pred_boxes = logo_pred_boxes.numpy()
        return logo_pred_boxes

class LogoEncoder(nn.Module):
    def __init__(self, siamese_model, ocr_model, matching_threshold, img_size: int = 224):
        super().__init__()
        self.siamese_model = siamese_model
        self.ocr_model = ocr_model
        self.img_size = img_size
        self.matching_threshold = matching_threshold
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Transformation pipeline
        mean = [0.5, 0.5, 0.5]
        std = [0.5, 0.5, 0.5]
        self.img_transforms = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ])

    def preprocess_image(self, img):
        img = Image.open(img) if isinstance(img, str) else img
        img = img.convert("RGBA").convert("RGB")
        # Pad to square
        pad_color = (255, 255, 255)
        img = ImageOps.expand(
            img,
            (
                (max(img.size) - img.size[0]) // 2,
                (max(img.size) - img.size[1]) // 2,
                (max(img.size) - img.size[0]) // 2,
                (max(img.size) - img.size[1]) // 2,
            ),
            fill=pad_color,
        )
        # Resize
        img = img.resize((self.img_size, self.img_size))
        return img

    def forward(self, img):
        img = self.preprocess_image(img)

        ocr_emb = ocr_main(image_path=img, model=self.ocr_model, height=None, width=None)[0]
        ocr_emb = ocr_emb[None, ...].to(self.device)
        img_tensor = self.img_transforms(img)[None, ...].to(self.device)
        logo_feat = self.siamese_model.features(img_tensor, ocr_emb)

        # L2 normalize
        logo_feat = l2_norm(logo_feat).squeeze(0)
        return logo_feat
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True)
    args = parser.parse_args()

    AWL_MODEL, SIAMESE_MODEL, OCR_MODEL, SIAMESE_THRE, LOGO_FEATS, LOGO_FILES, DOMAIN_MAP_PATH = load_config()
    logo_extractor = LogoDetector(AWL_MODEL)

    logo_encoder = LogoEncoder(SIAMESE_MODEL, OCR_MODEL, SIAMESE_THRE)

    API_KEY, SEARCH_ENGINE_ID = [x.strip() for x in open(configs.google_search_credentials).readlines()]

    knowledge_expansion = BrandKnowledgeConstruction(
        API_KEY, SEARCH_ENGINE_ID,
        logo_extractor, logo_encoder
    )

    # Automatically downloads and manages the ChromeDriver
    options = Options()
    options.add_argument("--headless")  # Run headless
    options.add_argument("--window-size=1920,1080")  # set resolution
    options.add_argument("--no-sandbox")  # (Linux) avoids sandbox issues
    options.add_argument("--disable-dev-shm-usage")  # Fixes shared memory errors
    options.add_argument("--disable-gpu")  # (Windows) GPU acceleration off in headless
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    for folder in os.listdir(args.folder):
        info_path = os.path.join(args.folder, folder, 'info.txt')
        shot_path = os.path.join(args.folder, folder, "shot.png")

        if len(open(info_path, encoding='ISO-8859-1').read()) > 0:
            URL = open(info_path, encoding='ISO-8859-1').read()
        else:
            URL = 'https://' + folder
        query_domain = tldextract.extract(URL).domain
        query_tld = tldextract.extract(URL).suffix

        reference_logo, company_domains, brand_name, company_logos, branch_time, status = \
            knowledge_expansion.run(webdriver=driver, shot_path=shot_path,
                                    query_domain=query_domain, query_tld=query_tld,
                                    type = 'domain2brand')

        # reference_logo, company_domains, brand_name, company_logos, branch_time, status = \
        #     knowledge_expansion.run(webdriver=driver, shot_path=shot_path,
        #                             query_domain=query_domain, query_tld=query_tld,
        #                             type = 'logo2brand')











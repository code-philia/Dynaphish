import tldextract
import os
import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))  # /git_space/Dynaphish

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from knowledge_expansion.brand_knowledge_online import BrandKnowledgeExpansion
import os
import numpy as np
import warnings
import configs as configs
import torch
import torch.nn as nn
from knowledge_expansion.phishintention.modules import pred_rcnn, find_element_type, ocr_main, l2_norm
from knowledge_expansion.phishintention.configs import load_config
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from PIL import Image, ImageOps
from torchvision import transforms
import pickle
from numpy.typing import ArrayLike, NDArray
from typing import Union, Tuple, Dict, List, Optional
warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.functional")

# todo: fill in your Google service account
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = configs.google_cloud_json_credentials

class LogoDetector(nn.Module):
    def __init__(self, predictor):
        super().__init__()
        self.predictor = predictor

    def forward(self, screenshot_path: str) -> NDArray:

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
        self.ocr_model     = ocr_model
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

    def forward(self, img: Union[str, Image.Image]) -> NDArray:
        ocr_emb = ocr_main(image_path=img, model=self.ocr_model)[0]
        ocr_emb = ocr_emb[None, ...].to(self.device)
        img_tensor = self.img_transforms(img)[None, ...].to(self.device)
        logo_feat = self.siamese_model.features(img_tensor, ocr_emb)

        # L2 normalize
        logo_feat = l2_norm(logo_feat).squeeze(0).detach().cpu().numpy()
        return logo_feat

class BrandKnowledgeHandler():
    def __init__(self, logo_features, logo_file_list, domain_map_path):
        self.logo_features = logo_features
        self.logo_file_list = logo_file_list
        self.domain_map_path = domain_map_path

    def brand_in_domainmap(self, new_brand: str) -> Tuple[Dict, bool]:
        with open(self.domain_map_path, 'rb') as handle:
            domain_map = pickle.load(handle)
        existing_brands = domain_map.keys()
        if new_brand in existing_brands:
            return domain_map, True
        return domain_map, False

    def logo_in_reflist(self, logo_feat: NDArray) -> bool:
        if (self.logo_features @ logo_feat >= logo_encoder.matching_threshold).any():
            return True
        else:
            return False

    def expand_reference(self,
                         new_brand_name: str,
                         new_domains: List[str],
                         new_logos: List[Optional[Image.Image]],
                         logo_encoder: LogoEncoder):
        domain_map, domain_in_target = self.brand_in_domainmap(new_brand=new_brand_name)

        if not domain_in_target:  # if this domain is not in targetlist ==> add it
            domain_map[new_brand_name] = list(set(new_domains))
            with open(self.domain_map_path, 'wb') as handle:
                pickle.dump(domain_map, handle)

        # expand logo list
        valid_logo = [a for a in new_logos if a is not None]
        if len(valid_logo) == 0:  # no valid logo
            return

        targetlist_path      = os.path.commonpath(self.logo_file_list.tolist())
        new_logo_save_folder = os.path.join(targetlist_path, new_brand_name)
        os.makedirs(new_logo_save_folder, exist_ok=True)

        exist_num_files = len(os.listdir(new_logo_save_folder))
        new_logo_save_paths = []
        for ct, logo in enumerate(valid_logo):
            this_logo_save_path = os.path.join(new_logo_save_folder, '{}.png'.format(exist_num_files + ct))
            if os.path.exists(this_logo_save_path):
                this_logo_save_path = os.path.join(new_logo_save_folder, '{}_expand.png'.format(exist_num_files + ct))
            logo.save(this_logo_save_path)
            new_logo_save_paths.append(this_logo_save_path)

        new_logo_feats = []
        new_file_name_list = []

        for logo_path in new_logo_save_paths:
            new_logo_feats.append(logo_encoder(reference_logo))
            new_file_name_list.append(str(logo_path))

        agg_logo_feats     = self.logo_features.tolist() + new_logo_feats
        agg_file_name_list = self.logo_file_list.tolist() + new_file_name_list

        # update reference list
        self.logo_features  = np.asarray(agg_logo_feats)
        self.logo_file_list = np.asarray(agg_file_name_list)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True)
    args = parser.parse_args()

    AWL_MODEL, SIAMESE_MODEL, OCR_MODEL, SIAMESE_THRE, \
        LOGO_FEATS, LOGO_FILES, DOMAIN_MAP_PATH = load_config()

    logo_extractor = LogoDetector(AWL_MODEL)
    logo_encoder   = LogoEncoder(SIAMESE_MODEL, OCR_MODEL, SIAMESE_THRE)

    API_KEY, SEARCH_ENGINE_ID = [x.strip() for x in open(configs.google_search_credentials).readlines()]

    knowledge_expansion = BrandKnowledgeExpansion(
        Search_API=API_KEY,
        Search_ID=SEARCH_ENGINE_ID,
        logo_extractor=logo_extractor,
        logo_encoder=logo_encoder
    )

    bkb = BrandKnowledgeHandler(
        logo_features=LOGO_FEATS,
        logo_file_list=LOGO_FILES,
        domain_map_path=DOMAIN_MAP_PATH
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

        ## Check whether the logo is in reference list already
        all_logos_coords = logo_extractor(shot_path)
        if len(all_logos_coords) == 0:
            continue
        logo_coord = all_logos_coords[0]
        screenshot_img = Image.open(shot_path)
        screenshot_img = screenshot_img.convert("RGB")
        reference_logo = screenshot_img.crop((int(logo_coord[0]), int(logo_coord[1]),
                                              int(logo_coord[2]), int(logo_coord[3])))
        logo_feat = logo_encoder(reference_logo)
        in_reflist = bkb.logo_in_reflist(logo_feat)

        if not in_reflist:
            ### Domain2brand (Popularity validation)
            reference_logo, company_domains, brand_name, company_logos, branch_time, status = \
                knowledge_expansion.run(webdriver=driver,
                                        shot_path=shot_path,
                                        query_domain=query_domain,
                                        query_tld=query_tld,
                                        type = 'domain2brand')
            brand_name = None # fixme
            if brand_name is None:
                ### Logo2brand (Representation validation)
                reference_logo, company_domains, brand_name, company_logos, branch_time, status = \
                    knowledge_expansion.run(webdriver=driver,
                                            shot_path=shot_path,
                                            query_domain=query_domain,
                                            query_tld=query_tld,
                                            type = 'logo2brand')

                if brand_name is None:
                    print("Cannot find brand")
                    continue

            company_logos.append(reference_logo)

            ## Expand reference list
            if len(company_logos):
                bkb.expand_reference(brand_name, company_domains, company_logos, logo_encoder)



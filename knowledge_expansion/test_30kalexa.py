import os
import tldextract
import time
import numpy as np
from tqdm import tqdm
from unidecode import unidecode
from xdriver.xutils.WebInteraction import WebInteraction
from xdriver.xutils.PhishIntentionWrapper import PhishIntentionWrapper
from xdriver.xutils.forms.SubmissionButtonLocator import SubmissionButtonLocator
from knowledge_expansion.brand_knowledge_online import BrandKnowledgeConstruction
from mmocr.apis import MMOCRInferencer
from field_study_logo2brand.dynaphish_main import DynaPhish
import CONFIGS as configs
import json
from xdriver.XDriver import XDriver
os.environ["CUDA_VISIBLE_DEVICES"]="1,0"

if __name__ == '__main__':

    driver = XDriver.boot(chrome=True)
    time.sleep(3)
    driver.set_page_load_timeout(20)
    driver.set_script_timeout(20)

    phishintention_config_path = './knowledge_expansion/configs_orig.yaml'
    PhishIntention = PhishIntentionWrapper(reload_targetlist=False)
    PhishIntention.reset_model(phishintention_config_path)

    API_KEY, SEARCH_ENGINE_ID = [x.strip() for x in open(configs.google_search_credentials).readlines()]
    KnowledgeExpansionModule = BrandKnowledgeConstruction(API_KEY, SEARCH_ENGINE_ID, PhishIntention)

    mmocr_model = MMOCRInferencer(det=None,
                        rec='ABINet',
                        device='cuda')
    button_locator_model = SubmissionButtonLocator(
        button_locator_config=configs.button_locator_config,
        button_locator_weights_path=configs.button_locator_weights_path)

    InteractionModel = WebInteraction(phishintention_cls=PhishIntention,
                                      mmocr_model=mmocr_model,
                                      button_locator_model=button_locator_model,
                                      interaction_depth=1)

    dynaphish = DynaPhish(PhishIntention, phishintention_config_path, InteractionModel, KnowledgeExpansionModule)
    #
    with open('/home/ruofan/Downloads/coco_train.json', "rb") as handle:
        alexa_training = json.load(handle)
    test_list=[x['file_name'].split('/')[0] for x in alexa_training["images"]]
    with open('/home/ruofan/Downloads/coco_test.json', "rb") as handle:
        alexa_test = json.load(handle)
    test_list.extend([x['file_name'].split('/')[0] for x in alexa_test["images"]])

    result_txt = './knowledge_expansion/alexa30k_cleaned_v3.txt'

    for num, folder in tqdm(enumerate(test_list)):
        url = folder
        query_domain = tldextract.extract(folder).domain
        query_tld = tldextract.extract(folder).suffix

        if os.path.exists(result_txt) and \
                folder in [x.strip().split('\t')[0] for x in open(result_txt, encoding='ISO-8859-1').readlines()]:
            continue

        new_brand_domains, new_brand_name, new_brand_logos, \
        knowledge_discovery_runtime, comment = \
            dynaphish.knowledge_expansion(driver=driver, URL=url,
                                          screenshot_path=None,
                                          branch='domain2brand')
        with open(result_txt, "a+", encoding='ISO-8859-1') as f:
            f.write(str(unidecode(folder)) + "\t")
            f.write(str(unidecode(url)) + "\t")
            if new_brand_domains:
                f.write(str(new_brand_domains) + "\t")
            else:
                f.write(str(None) + "\t")

            if new_brand_name:
                f.write(str(unidecode(new_brand_name)) + "\t")
            else:
                f.write(str(None) + "\t")

            if new_brand_logos:
                f.write(str(np.sum([x is not None for x in new_brand_logos]) > 0) + "\t")
            else:
                f.write(str(None) + "\t")

            f.write(str(knowledge_discovery_runtime) + "\t")
            f.write(str(comment) + "\n")
            f.close()

        if (num+1) % 100 == 0:
            driver.quit()
            driver = XDriver.boot(chrome=True)
            time.sleep(3)
            driver.set_page_load_timeout(20)
            driver.set_script_timeout(20)

    driver.quit()


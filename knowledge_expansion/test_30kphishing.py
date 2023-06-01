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
from mmocr.utils.ocr import MMOCR
from field_study_logo2brand.dynaphish_main import DynaPhish
import CONFIGS as configs
import torch
from xdriver.XDriver import XDriver

if __name__ == '__main__':
    torch.cuda.empty_cache()
    XDriver.set_headless()
    driver = XDriver.boot(chrome=True)
    time.sleep(5)  # fixme: you have to sleep sometime, otherwise the browser will keep crashing
    driver.set_page_load_timeout(20)
    driver.set_script_timeout(20)

    phishintention_config_path = './knowledge_expansion_phish/configs_orig_copy.yaml'
    PhishIntention = PhishIntentionWrapper()
    PhishIntention.reset_model(phishintention_config_path)

    API_KEY, SEARCH_ENGINE_ID = [x.strip() for x in open(configs.google_search_credentials).readlines()]
    KnowledgeExpansionModule = BrandKnowledgeConstruction(API_KEY, SEARCH_ENGINE_ID, PhishIntention)

    mmocr_model = MMOCR(det=None,
                        recog='ABINet',
                        device='cuda',
                        config_dir=configs.mmocr_config_path)
    button_locator_model = SubmissionButtonLocator(
        button_locator_config=configs.button_locator_config,
        button_locator_weights_path=configs.button_locator_weights_path)

    InteractionModel = WebInteraction(phishintention_cls=PhishIntention,
                                      mmocr_model=mmocr_model,
                                      button_locator_model=button_locator_model,
                                      interaction_depth=1)

    dynaphish = DynaPhish(PhishIntention, phishintention_config_path, InteractionModel, KnowledgeExpansionModule)

    test_folder = '/home/ruofan/Downloads/phish_sample_30k'
    result_txt = './datasets/phish30k.txt'

    for num, folder in tqdm(enumerate(os.listdir(test_folder)[26000:])):
        # folder = 'Deutsche Bank AG+2020-08-20-13`15`30'
        shot_path = os.path.join(test_folder, folder, 'shot.png')
        info_path = os.path.join(test_folder, folder, 'info.txt')

        if not os.path.exists(info_path):
            continue
        if not os.path.exists(shot_path):
            continue

        url = eval(open(info_path, encoding="ISO-8859-1").read())['url']
        query_domain = tldextract.extract(url).domain
        query_tld = tldextract.extract(url).suffix

        if os.path.exists(result_txt) and \
                folder in [x.strip().split('\t')[0] for x in open(result_txt, encoding='ISO-8859-1').readlines()]:
            continue

        new_brand_domains, new_brand_name, new_brand_logos, knowledge_discovery_runtime, comment = \
            dynaphish.knowledge_expansion(driver=driver, URL=url,
                                          screenshot_path=shot_path,
                                          branch='logo2brand')
        # exit()
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

        if (num+1) % 100 == 0:
            driver.quit()
            driver = XDriver.boot(chrome=True)
            time.sleep(5)  # fixme: you have to sleep sometime, otherwise the browser will keep crashing
            driver.set_page_load_timeout(20)
            driver.set_script_timeout(20)

    '''result'''
    # fp = 0
    # total = 0
    # runtime_B2 = []
    # for line in open(result_txt).readlines():
    #     line = line.rstrip('\n')
    #     folder, B2, time_B2 = line.split('\t')
    #     if len(eval(B2)) > 0:
    #         fp += 1
    #     runtime_B2.append(eval(time_B2))
    #     total += 1
    #
    # print('FP = ', fp/total)
    # print('Median/Avg runtime for domain2brand branch {}, {}'.format(np.median(runtime_B2), np.mean(runtime_B2)))



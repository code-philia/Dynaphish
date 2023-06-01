import selenium.common.exceptions
import tldextract
import yaml
from phishintention.src.OCR_siamese_utils.inference import pred_siamese_OCR
import pickle
from xdriver.xutils.Logger import Logger
from xdriver.xutils.WebInteraction import WebInteraction
from xdriver.xutils.PhishIntentionWrapper import PhishIntentionWrapper
from xdriver.xutils.forms.SubmissionButtonLocator import SubmissionButtonLocator
from knowledge_expansion.brand_knowledge_online import BrandKnowledgeConstruction
from knowledge_expansion.utils import *
import os
from PIL import Image
import numpy as np
from mmocr.apis import MMOCRInferencer
import time
import cv2
import re
from datetime import date, timedelta
import warnings
import CONFIGS as configs
from tqdm import tqdm
from xdriver.XDriver import XDriver
warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.functional")
os.environ["CUDA_VISIBLE_DEVICES"]="1"
# todo: fill in your Google service account
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = configs.google_cloud_json_credentials

class DynaPhish():

    def __init__(self, phishintention_cls, phishintention_config_path,
                 interaction_model, brandknowledge,
                 standard_sleeping_time=7, timeout=60):

        self.Phishintention = phishintention_cls
        self.phishintention_config_path = phishintention_config_path
        self.KnowledgeExpansion = brandknowledge
        self.Interaction = interaction_model
        self.standard_sleeping_time = standard_sleeping_time
        self.timeout = timeout

    def domain_already_in_targetlist(self, domain_map_path, new_brand):
        with open(domain_map_path, 'rb') as handle:
            domain_map = pickle.load(handle)
        existing_brands = domain_map.keys()

        if new_brand in existing_brands:
            return domain_map, True
        return domain_map, False

    def plot_layout(self, screenshot_path):
        screenshot_img = Image.open(screenshot_path)
        screenshot_img = screenshot_img.convert("RGB")
        screenshot_img_arr = np.asarray(screenshot_img)
        screenshot_img_arr = np.flip(screenshot_img_arr, -1)  # RGB2BGR
        pred_classes, pred_boxes, pred_scores = self.Phishintention.element_recognition_reimplement(
                                                                    img_arr=screenshot_img_arr,
                                                                    model=self.Phishintention.AWL_MODEL)
        plotvis = self.Phishintention.layout_vis(screenshot_path, pred_boxes, pred_classes)
        return plotvis

    def expand_targetlist(self, config_path, new_brand, new_domains, new_logos):

        # PhishIntention config file
        with open(config_path) as file:
            configs = yaml.load(file, Loader=yaml.FullLoader)

        # expand domain map
        domain_map, domain_in_target = self.domain_already_in_targetlist(
                                        domain_map_path=configs['SIAMESE_MODEL']['DOMAIN_MAP_PATH'],
                                        new_brand=new_brand)
        if not domain_in_target: # if this domain is not in targetlist ==> add it
            domain_map[new_brand] = list(set(new_domains))
            with open(configs['SIAMESE_MODEL']['DOMAIN_MAP_PATH'], 'wb') as handle:
                pickle.dump(domain_map, handle)

        # expand logo list
        valid_logo = [a for a in new_logos if a is not None]
        if len(valid_logo) == 0:  # no valid logo
            return

        targetlist_path = configs['SIAMESE_MODEL']['TARGETLIST_PATH'].split('.zip')[0]
        new_logo_save_folder = os.path.join(targetlist_path, new_brand)
        os.makedirs(new_logo_save_folder, exist_ok=True)

        exist_num_files = len(os.listdir(new_logo_save_folder))
        new_logo_save_paths = []
        for ct, logo in enumerate(valid_logo):
            this_logo_save_path = os.path.join(new_logo_save_folder, '{}.png'.format(exist_num_files + ct))
            if os.path.exists(this_logo_save_path):
                this_logo_save_path = os.path.join(new_logo_save_folder, '{}_expand.png'.format(exist_num_files + ct))
            logo.save(this_logo_save_path)
            new_logo_save_paths.append(this_logo_save_path)

        # expand cached logo features list
        prev_logo_feats = np.load(
            os.path.join(os.path.dirname(configs['SIAMESE_MODEL']['TARGETLIST_PATH']), 'LOGO_FEATS.npy'))
        prev_file_name_list = np.load(
            os.path.join(os.path.dirname(configs['SIAMESE_MODEL']['TARGETLIST_PATH']), 'LOGO_FILES.npy'))
        prev_logo_feats = prev_logo_feats.tolist()
        prev_file_name_list = prev_file_name_list.tolist()

        new_logo_feats = []
        new_file_name_list = []

        for logo_path in new_logo_save_paths:
            new_logo_feats.append(pred_siamese_OCR(img=logo_path,
                                                   model=self.Phishintention.SIAMESE_MODEL,
                                                   ocr_model=self.Phishintention.OCR_MODEL,
                                                   grayscale=False))
            new_file_name_list.append(str(logo_path))

        agg_logo_feats = prev_logo_feats + new_logo_feats
        agg_file_name_list = prev_file_name_list + new_file_name_list
        np.save(os.path.join(os.path.dirname(configs['SIAMESE_MODEL']['TARGETLIST_PATH']), 'LOGO_FEATS'),
                             np.asarray(agg_logo_feats))
        np.save(os.path.join(os.path.dirname(configs['SIAMESE_MODEL']['TARGETLIST_PATH']), 'LOGO_FILES'),
                             np.asarray(agg_file_name_list))

        # update reference list
        self.Phishintention.LOGO_FEATS = np.asarray(agg_logo_feats)
        self.Phishintention.LOGO_FILES = np.asarray(agg_file_name_list)

    def knowledge_expansion(self, driver, URL, screenshot_path, branch):

        query_domain = tldextract.extract(URL).domain
        query_tld = tldextract.extract(URL).suffix

        _, new_brand_domains, new_brand_name, new_brand_logos, knowledge_discovery_runtime, comment = \
            self.KnowledgeExpansion.runit_simplified(driver=driver,
                                                     shot_path=screenshot_path,
                                                     query_domain=query_domain,
                                                     query_tld=query_tld,
                                                     type=branch)

        '''If the found knowledge is not inside targetlist -> expand targetlist'''
        if len(new_brand_domains) and np.sum([x is not None for x in new_brand_logos]) > 0:
            self.expand_targetlist(config_path=self.phishintention_config_path,
                                   new_brand=new_brand_name,
                                   new_domains=new_brand_domains,
                                   new_logos=new_brand_logos)

        return new_brand_domains, new_brand_name, new_brand_logos, \
               knowledge_discovery_runtime, comment

    def test_phishpedia(self, URL, screenshot_path):

        phishpedia_runtime = 0
        knowledge_discovery_runtime = 0
        web_interaction_algo_time = 0
        web_interaction_total_time = 0
        brand_in_targetlist = False
        phish_category = 0
        phish_target = None
        knowledge_discovery_branch = None
        found_knowledge = False

        # Has a logo or not?
        has_logo, in_target_list = self.Phishintention.has_logo(screenshot_path=screenshot_path)

        start_time = time.time()
        phish_category, phish_target, plotvis, siamese_conf, time_breakdown, pred_boxes, pred_classes = \
            self.Phishintention.test_orig_phishpedia(URL, screenshot_path)
        phishpedia_runtime = time.time() - start_time

        return phish_category, phish_target, plotvis, has_logo, brand_in_targetlist, \
               found_knowledge, knowledge_discovery_branch, \
               str(phishpedia_runtime) + '|' + str(knowledge_discovery_runtime) + '|' + \
               str(web_interaction_algo_time) + '|' + str(web_interaction_total_time)

    def test_phishintention(self, URL, screenshot_path, dynamic_enabled=True):

        phishintention_runtime = 0
        knowledge_discovery_runtime = 0
        web_interaction_algo_time = 0
        web_interaction_total_time = 0
        brand_in_targetlist = False
        phish_category = 0
        phish_target = None
        knowledge_discovery_branch = None
        found_knowledge = False

        # Has a logo or not?
        has_logo, in_target_list = self.Phishintention.has_logo(screenshot_path=screenshot_path)

        start_time = time.time()
        if dynamic_enabled:
            ph_driver = XDriver.boot(chrome=True)
            time.sleep(self.standard_sleeping_time)
            ph_driver.set_page_load_timeout(self.timeout)
            ph_driver.set_script_timeout(self.timeout)
            phish_category, phish_target, plotvis, siamese_conf, dynamic, time_breakdown, pred_boxes, pred_classes = \
                self.Phishintention.test_orig_phishintention(URL, screenshot_path, ph_driver)
            ph_driver.quit()
        else:
            phish_category, phish_target, plotvis, siamese_conf, dynamic, time_breakdown, pred_boxes, pred_classes = \
                self.Phishintention.test_orig_phishintention_wo_dynamic(URL, screenshot_path, driver)
        phishintention_runtime = time.time() - start_time

        return phish_category, phish_target, plotvis, has_logo, brand_in_targetlist, found_knowledge, knowledge_discovery_branch, \
               str(phishintention_runtime) + '|' + str(knowledge_discovery_runtime) + '|' + str(
                   web_interaction_algo_time) + '|' + str(web_interaction_total_time)

    def test_dynaphish(self, URL, screenshot_path, kb_driver, interaction_driver,
                       base_model, knowledge_expansion_branch,
                       kb_enabled=True, wi_enabled=True):

        phishpedia_runtime = 0
        knowledge_discovery_runtime = 0
        web_interaction_algo_time = 0
        web_interaction_total_time = 0
        brand_in_targetlist = False
        phish_category = 0
        phish_target = None
        knowledge_discovery_branch = None
        found_knowledge = False
        interaction_success = True
        redirection_evasion, no_verification = False, False
        plotvis = None

        # Has a logo or not?
        has_logo, in_target_list = self.Phishintention.has_logo(screenshot_path=screenshot_path)
        print('Has logo? {} Is in targetlist? {}'.format(has_logo, in_target_list))

        # domain(w)
        query_domain, query_tld = tldextract.extract(URL).domain, tldextract.extract(URL).suffix

        '''Ignore domain hosting site'''
        try:
            interaction_driver.get(URL)
            time.sleep(self.standard_sleeping_time)
            title = interaction_driver.title
            domain = tldextract.extract(URL).domain + '.' + tldextract.extract(URL).suffix
            if domain in title.lower() or re.search(OnlineForbiddenWord.WEBHOSTING_TEXT, title, re.IGNORECASE):
                print('Hit forbidden words')
                return phish_category, phish_target, plotvis, \
                       has_logo, brand_in_targetlist, \
                       found_knowledge, knowledge_discovery_branch, \
                       str(phishpedia_runtime) + '|' + str(knowledge_discovery_runtime) + '|' + str(
                           web_interaction_algo_time) + '|' + str(web_interaction_total_time), \
                       str(interaction_success) + '|' + str(redirection_evasion) + '|' + str(no_verification)
        except Exception as e:
            print(e)
            pass

        # If rep(w)!=null, i.e. has logo
        if has_logo:
            if in_target_list: # rep(w) in Ref, i.e. brand is in targetlist
                '''Report as phishing'''
                brand_in_targetlist = True
                start_time = time.time()
                if base_model == 'phishpedia':
                    phish_category, phish_target, plotvis, siamese_conf, time_breakdown, pred_boxes, pred_classes = \
                        self.Phishintention.test_orig_phishpedia(URL, screenshot_path)
                elif base_model == 'phishintention':
                    ph_driver = XDriver.boot(chrome=True)
                    time.sleep(self.standard_sleeping_time); ph_driver.set_page_load_timeout(self.timeout); ph_driver.set_script_timeout(self.timeout)
                    phish_category, phish_target, plotvis, siamese_conf, dynamic, time_breakdown, pred_boxes, pred_classes = \
                        self.Phishintention.test_orig_phishintention(URL, screenshot_path, ph_driver)
                    ph_driver.quit()
                else:
                    raise NotImplementedError

                phishpedia_runtime = time.time() - start_time

                return phish_category, phish_target, plotvis, \
                       has_logo, brand_in_targetlist, \
                       found_knowledge, knowledge_discovery_branch, \
                       str(phishpedia_runtime) + '|' + str(knowledge_discovery_runtime) + '|' + str(
                           web_interaction_algo_time) + '|' + str(web_interaction_total_time), \
                       str(interaction_success) + '|' + str(redirection_evasion) + '|' + str(no_verification)

            else: # rep(w) not in Ref, i.e. brand is not in targetlist
                if kb_enabled:
                    _, new_brand_domains, new_brand_name, new_brand_logos, knowledge_discovery_runtime, knowledge_discovery_branch = \
                        self.KnowledgeExpansion.runit_simplified(kb_driver, screenshot_path, query_domain, query_tld, knowledge_expansion_branch)
                else:
                    new_brand_domains, new_brand_logos = [], []

                '''If the found knowledge is not inside targetlist -> expand targetlist -> run phishintention AGAIN'''
                # w_target != null
                if len(new_brand_domains) > 0 and np.sum([x is not None for x in new_brand_logos]) > 0:
                    # Ref* <- Ref* + <domain(w_target), rep(w_target)>
                    self.expand_targetlist(config_path=self.phishintention_config_path,
                                           new_brand=new_brand_name,
                                           new_domains=new_brand_domains,
                                           new_logos=new_brand_logos)

                    print('==== New brand added ====')
                    start_time = time.time()
                    if base_model == 'phishpedia':
                        phish_category, phish_target, plotvis, siamese_conf, time_breakdown, pred_boxes, pred_classes = \
                                                self.Phishintention.test_orig_phishpedia(URL, screenshot_path)
                    elif base_model == 'phishintention':
                        ph_driver = XDriver.boot(chrome=True)
                        time.sleep(self.standard_sleeping_time); ph_driver.set_page_load_timeout(self.timeout); ph_driver.set_script_timeout(self.timeout)
                        phish_category, phish_target, plotvis, siamese_conf, dynamic, time_breakdown, pred_boxes, pred_classes = \
                            self.Phishintention.test_orig_phishintention(URL, screenshot_path, ph_driver)
                        ph_driver.quit()
                    else:
                        raise NotImplementedError
                    phishpedia_runtime = time.time() - start_time

                    return phish_category, phish_target, plotvis, \
                           has_logo, brand_in_targetlist, \
                           found_knowledge, knowledge_discovery_branch, \
                            str(phishpedia_runtime)+'|'+str(knowledge_discovery_runtime)+'|'+str(web_interaction_algo_time)+'|'+str(web_interaction_total_time), \
                           str(interaction_success) + '|' + str(redirection_evasion) + '|' + str(no_verification)

                # w_target = null, and WI is activated
                elif wi_enabled:
                    ''' Cannot find its knowledge -> behaviour intention'''
                    try:
                        print('Enter webinteraction')
                        is_benign, web_interaction_algo_time, web_interaction_total_time, \
                            redirection_evasion, no_verification = self.Interaction.get_benign_stricter(URL, interaction_driver)
                        print('Results after webinteraction, benign = {}'.format(is_benign))
                        if len(interaction_driver.window_handles) > 1:  # clean_up_window() has fatal error sometimes, mightbe because phishers draw a new browser himself, we cannot switch back to the original window
                            interaction_success = False
                        else:
                            phish_category = 0 if is_benign is None or is_benign == True else 1
                            return phish_category, None, plotvis, \
                                   has_logo, brand_in_targetlist, \
                                   found_knowledge, knowledge_discovery_branch, \
                                   str(phishpedia_runtime) + '|' + str(knowledge_discovery_runtime) + '|' + str(
                                       web_interaction_algo_time) + '|' + str(web_interaction_total_time), \
                                   str(interaction_success) + '|' + str(redirection_evasion) + '|' + str(
                                       no_verification)

                    except selenium.common.exceptions.TimeoutException:
                        pass
                    except:
                        interaction_success = False

        # If rep(w)=null, i.e. no logo
        elif wi_enabled:
            '''Else No logo -> behaviour intention'''
            try:
                print('Enter webinteraction')
                is_benign, web_interaction_algo_time, web_interaction_total_time, \
                    redirection_evasion, no_verification = self.Interaction.get_benign_stricter(URL, interaction_driver)
                print('Results after webinteraction, benign = {}'.format(is_benign))
                if len(interaction_driver.window_handles) > 1:  # clean_up_window() has fatal error sometimes, mightbe because phishers draw a new browser himself, we cannot switch back to the original window
                    interaction_success = False
                else:
                    phish_category = 0 if is_benign is None or is_benign == True else 1
                    return phish_category, None, plotvis, \
                           has_logo, brand_in_targetlist, \
                           found_knowledge, knowledge_discovery_branch, \
                           str(phishpedia_runtime) + '|' + str(knowledge_discovery_runtime) + '|' + str(
                               web_interaction_algo_time) + '|' + str(web_interaction_total_time), \
                           str(interaction_success) + '|' + str(redirection_evasion) + '|' + str(no_verification)

            except selenium.common.exceptions.TimeoutException:
                pass
            except Exception as e:
                print(e)
                interaction_success = False

        return 0, None, plotvis, \
               has_logo, brand_in_targetlist, \
               found_knowledge, knowledge_discovery_branch, \
               str(phishpedia_runtime) + '|' + str(knowledge_discovery_runtime) + '|' + str(
                   web_interaction_algo_time) + '|' + str(web_interaction_total_time), \
               str(interaction_success) + '|' + str(redirection_evasion) + '|' + str(no_verification)


    def test_on_folder_dynaphish(self, result_txt, test_folder, base_model,
                                 process_num=5000, headless=True, knowledge_expansion=True,
                                 knowledge_expansion_branch='logo2brand'):

        if headless:
            XDriver.set_headless()
        interaction_driver = XDriver.boot(chrome=True)
        time.sleep(self.standard_sleeping_time)  # fixme: you have to sleep sometime, otherwise the browser will keep crashing
        interaction_driver.set_page_load_timeout(self.timeout)
        interaction_driver.set_script_timeout(self.timeout)

        if knowledge_expansion:
            kb_driver = XDriver.boot(chrome=True)
            time.sleep(self.standard_sleeping_time)
            kb_driver.set_page_load_timeout(self.timeout)
            kb_driver.set_script_timeout(self.timeout)

        if not os.path.exists(result_txt):
            with open(result_txt, "w+") as f:
                f.write("folder" + "\t")
                f.write("url" + "\t")
                f.write("phish_prediction" + "\t")
                f.write("target_prediction" + "\t")  # write top1 prediction only
                f.write("has_logo" + "\t")  # write top1 prediction only
                f.write("brand_inside_targetlist" + "\t")
                f.write("found_knowledge" + "\t")
                f.write("knowledge_discovery_branch" + "\t")
                f.write("runtime_breakdown(PhishIntention|Knowledge_discovery|Web_interaction)" + "\n")
        #
        for ct, folder in tqdm(enumerate(os.listdir(test_folder)[:min(process_num, len(os.listdir(test_folder)))])):
            Logger.set_debug_on()
            if folder in [x.split('\t')[0] for x in open(result_txt, encoding='ISO-8859-1').readlines()]:
                continue

            info_path = os.path.join(test_folder, folder, 'info.txt')
            shot_path = os.path.join(test_folder, folder, 'shot.png')
            if not os.path.exists(shot_path):
                continue

            try:
                if len(open(info_path, encoding='ISO-8859-1').read()) > 0:
                    url = open(info_path, encoding='ISO-8859-1').read()
                else:
                    url = 'https://' + folder
            except:
                url = 'https://' + folder


            phish_category, phish_target, plotvis, has_logo, brand_in_targetlist, \
            found_knowledge, knowledge_discovery_branch, runtime_breakdown, interaction_success = \
                self.test_dynaphish(URL=url, screenshot_path=shot_path, kb_driver=kb_driver,
                                    interaction_driver=interaction_driver, base_model=base_model,
                                    knowledge_expansion_branch=knowledge_expansion_branch,
                                    kb_enabled=knowledge_expansion, wi_enabled=True)


            # write results as well as predicted image
            try:
                with open(result_txt, "a+", encoding='ISO-8859-1') as f:
                    f.write(folder + "\t")
                    f.write(url + "\t")
                    f.write(str(phish_category) + "\t")
                    f.write(str(phish_target) + "\t")  # write top1 prediction only
                    f.write(str(has_logo) + "\t")
                    f.write(str(brand_in_targetlist) + "\t")
                    f.write(str(found_knowledge) + "\t")
                    f.write(str(knowledge_discovery_branch) + "\t")
                    f.write(runtime_breakdown + "\n")

                if plotvis is not None:
                    cv2.imwrite(os.path.join(test_folder, folder, "predict_dyna{}.png".format(base_model)), plotvis)
            except UnicodeEncodeError:
                continue

            if interaction_success.startswith('False') or (ct+501)%500 == 0:
                interaction_driver.quit()
                interaction_driver = XDriver.boot(chrome=True)
                time.sleep(self.standard_sleeping_time)  # fixme: you have to sleep sometime, otherwise the browser will keep crashing
                interaction_driver.set_page_load_timeout(self.timeout)
                interaction_driver.set_script_timeout(self.timeout)
            if knowledge_expansion and (ct+501)%500 == 0:
                kb_driver.quit()
                kb_driver = XDriver.boot(chrome=True)
                time.sleep(self.standard_sleeping_time)
                kb_driver.set_page_load_timeout(self.timeout)
                kb_driver.set_script_timeout(self.timeout)

        interaction_driver.quit()
        if knowledge_expansion: kb_driver.quit()


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", help='model to run', default='phishintention')
    parser.add_argument("--verbose", action='store_true')
    parser.add_argument("--branch", default='logo2brand')
    parser.add_argument("--headless", default=False)
    parser.add_argument("--folder", required=True)
    args = parser.parse_args()

    phishintention_config_path = './field_study_logo2brand/configs.yaml'
    PhishIntention = PhishIntentionWrapper()
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

    os.makedirs('./field_study_logo2brand/results/', exist_ok=True)
    if args.verbose:
        Logger.set_debug_on()

    from datetime import datetime
    # Get today's date
    today = datetime.today()
    # Format the date as a string in the "%Y-%m-%d" format
    today_date = today.strftime("%Y-%m-%d")
    result_txt = './field_study_logo2brand/results/{}_dynaintention.txt'.format(today_date)
    dynaphish.test_on_folder_dynaphish(result_txt=result_txt,
                                       test_folder=args.folder, #os.path.join(server_add, today_date)
                                       headless=args.headless,
                                       base_model=args.base_model,
                                       knowledge_expansion_branch=args.branch)






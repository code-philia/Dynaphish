from tqdm import tqdm
import whois
import os
import tldextract
import datetime
from dateutil import parser
import numpy as np

if __name__ == '__main__':

    test_folder1 = './datasets/bottom10k_alexa.txt'
    test_folder2 = './datasets/middle10k_alexa.txt'
    test_folder3 = './datasets/top10k_alexa.txt'

    result_txt = './datasets/alexa30k_lifespan.txt'
    all_alexa_urls = [x.split('\t')[0] for x in open(test_folder1, encoding='ISO-8859-1').readlines()[1:]] + \
                     [x.split('\t')[0] for x in open(test_folder2, encoding='ISO-8859-1').readlines()[1:]] + \
                     [x.split('\t')[0] for x in open(test_folder3, encoding='ISO-8859-1').readlines()[1:]]

    for num, folder in tqdm(enumerate(all_alexa_urls)):
        shot_path = os.path.join(test_folder1, folder, 'shot.png')
        query_domain = tldextract.extract(folder).domain
        query_tld = tldextract.extract(folder).suffix
        domain_tocheck = query_domain + '.' + query_tld

        if os.path.exists(result_txt) and folder in [x.split('\t')[0] for x in open(result_txt).readlines()]:
            continue

        try:
            whois_info = whois.whois(domain_tocheck)
            if 'creation_date' in list(whois_info.keys()):
                pub_date = whois_info['creation_date']
                if isinstance(pub_date, list):
                    pub_date = pub_date[0]
            elif 'updated_date' in list(whois_info.keys()):
                pub_date = whois_info['updated_date']
                if isinstance(pub_date, list):
                    pub_date = pub_date[0]
            else:
                print(whois_info)
                pub_date = None
            print(pub_date)
        except whois.parser.PywhoisError as e:
            pub_date = None
        except UnicodeError:
            continue

        try:
            with open(result_txt, 'a+') as f:
                f.write(folder+'\t'+str(pub_date)+'\n')
        except:
            continue


    # average time to now
    days_till_now = []
    for line in open(result_txt).readlines():
        pub_date = line.strip().split('\t')[1]
        if pub_date != 'None':
            try:
                days_till_now.append((datetime.datetime.today() - parser.parse(pub_date)).days)
            except:
                continue

    print(np.mean(days_till_now) / 30 / 12)
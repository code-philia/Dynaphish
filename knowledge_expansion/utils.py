import numpy as np
import cv2
from seleniumwire import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import re
import sys
from unidecode import unidecode
from urllib.parse import parse_qs, urljoin, urlparse, urlsplit, urlunsplit
from dateutil.parser import parse
import dateutil
import tldextract

class OnlineForbiddenWord():
    IGNORE_DOMAINS = ['wikipedia', 'wiki',
                      'bloomberg', 'glassdoor',
                      'linkedin', 'jobstreet',
                      'facebook', 'twitter',
                      'instagram', 'youtube', 'org', 'accounting']

    # ignore those webhosting/domainhosting sites
    WEBHOSTING_TEXT = '(webmail.*)|(.*godaddy.*)|(.*roundcube.*)|(.*clouddns.*)|(.*namecheap.*)|(.*plesk.*)|(.*rackspace.*)|(.*cpanel.*)|(.*virtualmin.*)|(.*control.*webpanel.*)|(.*hostgator.*)|(.*mirohost.*)|(.*hostinger.*)|(.*bisecthosting.*)|(.*misshosting.*)|(.*serveriai.*)|(.*register\.to.*)|(.*appspot.*)|' \
                      '(.*weebly.*)|(.*serv5.*)|(.*weebly.*)|(.*umbler.*)|(.*joomla.*)' \
                      '(.*webnode.*)|(.*duckdns.*)|(.*moonfruit.*)|(.*netlify.*)|' \
                      '(.*glitch.*)|(.*herokuapp.*)|(.*yolasite.*)|(.*dynv6.*)|(.*cdnvn.*)|' \
                      '(.*surge.*)|(.*myshn.*)|(.*azurewebsites.*)|(.*dreamhost.*)|host|cloak|domain|block|isp|azure|wordpress|weebly|dns|network|shortener|server|helpdesk|laravel|jellyfin|portainer|reddit|storybook'

    WEBHOSTING_DOMAINS = ['godaddy', 'roundcube',
                          'clouddns', 'namecheap',
                          'plesk', 'rackspace', 'cpanel',
                          'virtualmin', 'control-webpanel',
                          'hostgator', 'mirohost', 'hostinger',
                          'bisecthosting', 'misshosting', 'serveriai',
                          'register', 'appspot', 'weebly', 'serv5',
                          'weebly', 'umbler', 'joomla', 'webnode', 'duckdns',
                          'moonfruit', 'netlify', 'glitch', 'herokuapp',
                          'yolasite', 'dynv6', 'cdnvn', 'surge', 'myshn',
                          'azurewebsites', 'dreamhost', 'proisp',
                          'accounting']


def get_web_pub_dates(search_item):
    try:  # check gooogle search returned publication time
        pub_date = parse(search_item.get('pagemap').get('metatags')[0].get('article:published_time')).replace(
            tzinfo=None)
    except (TypeError, AttributeError, dateutil.parser.ParserError):
        pub_date = ''
    return pub_date

def reduce_to_main_domain(urls_list):
    reduced_list = []
    for url in urls_list:
        parsed_url = urlparse(url)
        reduced_url = parsed_url.scheme + '://' + \
                      tldextract.extract(parsed_url.hostname).domain + '.' + \
                      tldextract.extract(parsed_url.hostname).suffix
        reduced_list.append(reduced_url)
    return reduced_list

def query_cleaning(query: str):

    if len(query) == 0:
        return ''
    if query.lower().startswith('index of') or \
        'forbidden' in query.lower() or \
        'access denied' in query.lower() or\
        'bad gateway' in query.lower() or \
        'not found' in query.lower():
        return ''
    if query.lower() in ['text', 'logo', 'graphics']:
        return ''
    if query.lower() == 'tm':
        return ''
    # remove noisy tokens
    for it, token in enumerate(query.split('\n')):
        if len(token) <= 1:
            continue
        # noisy token
        elif any(char.isdigit() for char in token) and any(char.isalpha() for char in token) and any(((not char.isalnum()) and (not char.isspace())) for char in token):
            continue
        else:
            query = ' '.join(query.split('\n')[it:])
            break

    for it, token in enumerate(query.split(' ')):
        if len(token) <= 2 or token.isnumeric():
            continue
        else:
            query = ' '.join(query.split(' ')[it:])
            break

    query = query.translate(str.maketrans('', '', r"""!"#$%'()*+,-/:;<=>?@[\]^_`{|}~"""))
    return query


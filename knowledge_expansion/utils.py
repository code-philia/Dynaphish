from dataclasses import dataclass
from typing import ClassVar, List, Pattern
import re
from typing import Any, Iterable, List, Optional
from datetime import datetime
from urllib.parse import urlparse
import tldextract
from dateutil import parser as dateparser
import string
@dataclass(frozen=True)
class OnlineForbiddenWord:
    IGNORE_DOMAINS: ClassVar[List[str]] = [
        "wikipedia", "wiki", "bloomberg", "glassdoor",
        "linkedin", "jobstreet", "facebook", "twitter",
        "instagram", "youtube", "org", "accounting",
    ]
    WEBHOSTING_DOMAINS: ClassVar[List[str]] = [
        "godaddy", "roundcube", "clouddns", "namecheap", "plesk", "rackspace",
        "cpanel", "virtualmin", "control-webpanel", "hostgator", "mirohost",
        "hostinger", "bisecthosting", "misshosting", "serveriai", "register",
        "appspot", "weebly", "serv5", "umbler", "joomla", "webnode", "duckdns",
        "moonfruit", "netlify", "glitch", "herokuapp", "yolasite", "dynv6",
        "cdnvn", "surge", "myshn", "azurewebsites", "dreamhost", "proisp",
        "accounting",
    ]
    _FRAGMENTS: ClassVar[List[str]] = [
        r"webmail.*", r".*godaddy.*", r".*roundcube.*", r".*clouddns.*", r".*namecheap.*",
        r".*plesk.*", r".*rackspace.*", r".*cpanel.*", r".*virtualmin.*", r".*control.*webpanel.*",
        r".*hostgator.*", r".*mirohost.*", r".*hostinger.*", r".*bisecthosting.*", r".*misshosting.*",
        r".*serveriai.*", r"register\.to.*", r".*appspot.*", r".*weebly.*", r".*serv5.*",
        r".*umbler.*", r".*joomla.*", r".*webnode.*", r".*duckdns.*", r".*moonfruit.*",
        r".*netlify.*", r".*glitch.*", r".*herokuapp.*", r".*yolasite.*", r".*dynv6.*",
        r".*cdnvn.*", r".*surge.*", r".*myshn.*", r".*azurewebsites.*", r".*dreamhost.*",
        r"host", r"cloak", r"domain", r"block", r"isp", r"azure", r"wordpress",
        r"weebly", r"dns", r"network", r"shortener", r"server", r"helpdesk",
        r"laravel", r"jellyfin", r"portainer", r"reddit", r"storybook",
    ]
    WEBHOSTING_TEXT: ClassVar[Pattern[str]] = re.compile("|".join(f"(?:{f})" for f in _FRAGMENTS), re.IGNORECASE)


def get_web_pub_dates(search_item: dict[str, Any]) -> Optional[datetime]:
    try:
        metatags = search_item.get("pagemap", {}).get("metatags", []) or []
    except AttributeError:
        return None

    # Try common keys in order of relevance
    keys = [
        "article:published_time", "article:modified_time",
        "og:published_time", "og:updated_time",
        "datePublished", "date", "pubdate",
    ]

    for mt in metatags:
        if not isinstance(mt, dict):
            continue
        for k in keys:
            val = mt.get(k)
            if not val:
                continue
            try:
                dt = dateparser.parse(val)
                if not dt:
                    continue
                # Return naive (drop tz) to match your original behavior
                return dt.replace(tzinfo=None)
            except (ValueError, TypeError, dateparser.ParserError):
                continue
    return None

def reduce_to_main_domain(urls_list: Iterable[str]) -> List[str]:
    out:  List[str] = []
    seen: set[str] = set()

    for url in urls_list:
        try:
            p = urlparse(url)
        except Exception:
            continue

        scheme = p.scheme or "https"
        host   = p.hostname  # None for non-HTTP schemes or malformed URLs
        if not host:
            continue

        ext = tldextract.extract(host)
        if ext.suffix:  # normal domain
            reg_domain = f"{ext.domain}.{ext.suffix}" if ext.domain else host
        else:
            reg_domain = host

        reduced = f"{scheme}://{reg_domain.lower()}"
        if reduced not in seen:
            seen.add(reduced)
            out.append(reduced)

    return out

def query_cleaning(query: str) -> str:
    q = (query or '').strip()
    if not q: return ''
    low = q.lower()
    if low.startswith('index of') or any(k in low for k in ('forbidden','access denied','bad gateway','not found')): return ''
    if low in ('text','logo','graphics','tm'): return ''

    # drop leading noisy lines (alnum+digits+symbols)
    lines = q.splitlines()
    for i, line in enumerate(lines):
        if len(line) > 1 and not (any(c.isdigit() for c in line) and any(c.isalpha() for c in line) and any((not c.isalnum()) and (not c.isspace()) for c in line)):
            q = '\n'.join(lines[i:]); break

    # drop leading short/numeric tokens
    parts = q.split()
    for i, tok in enumerate(parts):
        if len(tok) > 2 and not tok.isnumeric():
            q = ' '.join(parts[i:]); break

    q = q.translate(str.maketrans('', '', string.punctuation))
    return ' '.join(q.split())

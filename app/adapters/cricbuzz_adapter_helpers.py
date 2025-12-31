from bs4 import BeautifulSoup
import re
import json
from typing import List, Any


def extract_json_from_html(html: str) -> List[Any]:
    blobs = []
    try:
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup.find_all('script', type='application/ld+json'):
            try:
                parsed = json.loads(tag.string)
                blobs.append(parsed)
            except Exception:
                continue
    except Exception:
        pass

    patterns = [r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', r'window\.__DATA__\s*=\s*(\{.*?\});', r'initialState\s*=\s*(\{.*?\});', r'var\s+initialState\s*=\s*(\{.*?\});']
    for pat in patterns:
        try:
            m = re.search(pat, html, flags=re.S)
            if m:
                j = m.group(1)
                try:
                    parsed = json.loads(j)
                    blobs.append(parsed)
                except Exception:
                    try:
                        j2 = j.rstrip(';')
                        parsed = json.loads(j2)
                        blobs.append(parsed)
                    except Exception:
                        continue
        except Exception:
            continue
    return blobs

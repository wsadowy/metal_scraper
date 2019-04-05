import re

from scrapy.http import HtmlResponse


def increment_paginated_url(url, increment_by=500):
    regex = r'iDisplayStart={}'
    src_regex = regex.format(r'(\w+)')
    page_nr = re.search(src_regex, url).group(1)
    return re.sub(src_regex, regex.format(int(page_nr) + increment_by), url)


def responsify(fpath):
    with open(fpath, 'r') as f:
        payload = f.read()
        return HtmlResponse('www.example.com', body=payload, encoding='utf-8')

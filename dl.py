import argparse
import bs4
import collections
import logging
import os
import pathlib
import re
import requests
import urllib.parse
import urllib.request

parser = argparse.ArgumentParser(
    description='Download files from links in a page.')
parser.add_argument(
    '--base-url',
    default=('http://clapi.ish-lyon.cnrs.fr/'),
    help='base_url')
parser.add_argument(
    '--url',
    default=('http://clapi.ish-lyon.cnrs.fr/V3_Telecharger.php'),
    help='url to get the files urls from')
parser.add_argument(
    '--out-dir',
    default='data',
    help='output directory')
args = parser.parse_args()

pathlib.Path(args.out_dir).mkdir(parents=True, exist_ok=True)

logging.basicConfig(format='[%(name)s] %(levelname)s %(message)s')
logger = logging.getLogger('dl')
logger.setLevel(logging.INFO)

session = requests.Session()
request = session.get(args.url)

soup =  bs4.BeautifulSoup(request.text, 'html.parser')

re_url = re.compile("""
(?:
  javascript\:window\.location\.href='(.*)';
)
|
(?:
  javascript:window\.open\('(.*)','_blank'\);
)
""",
                    re.X)

re_name = re.compile('filename=(.*)')

def job(link, out_dir):
    try:
        content = session.get(link, headers={
            'Host': 'clapi.ish-lyon.cnrs.fr',
            'Accept': '*/*;q=0.8',
            'Referer': 'http://clapi.ish-lyon.cnrs.fr/V3_Telecharger.php',
            'Connection': 'keep-alive'
        })
        name = re_name.search(content.headers['Content-Disposition']).group(1)
        path = os.path.join(out_dir, name)
        with open(path, 'wb') as fh:
            for chunk in content.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fh.write(chunk)
    except Exception as e:
        logger.error('Error for url {}: {}'.format(link, e))

def get_links(tr):
    imgs = tr.find_all('img', {'src': 'V3_Images/telecharger.png'})
    links = []
    for img in imgs:
        match = re_url.match(img.get('onclick'))
        if match is not None:
            if match.group(1):
                url = match.group(1)
            elif match.group(2):
                url = match.group(2)
        links.append(urllib.parse.urljoin(args.base_url, url))
    return links

group = None
for tr in soup.find_all('tr'):
    if tr.get('bgcolor') == '#BCA9F5':
        group = tr.find('td').get_text()
    else:
        tds = tr.find_all('td')
        assert len(tds) > 0
        subgroup = tds[0].get_text().strip()
        if group and subgroup: 
            out_dir = os.path.join(args.out_dir,
                                   group,
                                   subgroup)
            pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    links = get_links(tr)
    for link in links:
        job(link, out_dir)

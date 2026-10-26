"""Public package checks and expiring news-map maintenance; no model/API fees."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from datetime import datetime, timedelta, timezone
import urllib.request
import xml.etree.ElementTree as ET
import time

BRANDS = ('oyunpiksel', 'bytepusula', 'perdepop')
NS = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
NEWS = '{http://www.google.com/schemas/sitemap-news/0.9}'
BASE = Path(__file__).resolve().parent
# News entries need not fill the entire allowed 48-hour window. Keep a 12-hour
# safety margin for delayed scheduled jobs, queues and deployments. This only
# trims the news sitemap, never article pages, regular sitemap or RSS.
NEWS_RETENTION = timedelta(hours=36)

def validate(brand):
    record = json.loads((BASE/'release-manifest.json').read_text(encoding='utf-8'))['brands'][brand]
    root = BASE/'sites'/brand
    files = [p for p in root.rglob('*') if p.is_file()]
    if len(files) != record['files'] or len(record['sha256']) != len(files) or record['articles'] < 1:
        raise ValueError('Empty or changed package file count')
    for path in files:
        rel = path.relative_to(root).as_posix()
        if path.is_symlink() or path.suffix not in ('.html','.xml','.svg','.css','.js','.txt','.json','.png'):
            raise ValueError('Unsafe public file')
        if path.suffix == '.png' and (not re.fullmatch(r'assets/covers/[a-z0-9-]+\.png', rel)
                or not path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')):
            raise ValueError('Only verified PNG covers allowed')
        if re.search(r'(?i)(^|/)(private|secrets|credentials)(/|$)|(^|/)\.env($|\.)|(^|/)(deployment-)?token(\.[^/]*)?$|\.(sql|dump|pem|key|pfx)(\.gz)?$', rel):
            raise ValueError('Private path in public package')
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256'].get(rel):
            raise ValueError('Checksum mismatch: '+rel)
    for path in root.glob('*/index.html'):
        text = path.read_text(encoding='utf-8')
        expected = 'https://'+brand+'.com/'+path.parent.name+'/'
        if len(re.findall('rel="canonical"', text)) != 1 or f'href="{expected}"' not in text:
            raise ValueError('Canonical mismatch')
    return root

def request(url):
    req = urllib.request.Request(url, headers={'User-Agent':'MediaReleaseHealth/1.0 (not reader traffic)'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.status, response.read()

def prune(data, now=None):
    root = ET.fromstring(data)
    if root.tag != NS+'urlset':
        raise ValueError('Unexpected news sitemap')
    now = datetime.now(timezone.utc) if now is None else now
    removed = 0
    for node in list(root):
        raw = node.findtext(NEWS+'news/'+NEWS+'publication_date')
        stamp = datetime.fromisoformat(raw or '')
        if stamp.tzinfo is None or stamp > now:
            raise ValueError('Invalid news publication timestamp')
        if stamp < now-NEWS_RETENTION:
            root.remove(node)
            removed += 1
    return ET.tostring(root, encoding='unicode'), removed

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('brand', choices=BRANDS)
    parser.add_argument('--scheduled', choices=('true','false'), default='false')
    parser.add_argument('--verify-live', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    root = BASE/'sites'/args.brand
    if args.verify_live:
        for rel in ('index.html','news-sitemap.xml'):
            for attempt in range(10):
                status, data = request('https://'+args.brand+'.com/'+('' if rel == 'index.html' else rel))
                if status == 200 and data == (root/rel).read_bytes():
                    break
                if attempt == 9:
                    raise SystemExit('Live content differs from reviewed package: '+rel)
                time.sleep(5)
        print('PASS: custom-domain homepage and news sitemap match deployed package.')
        return
    root = validate(args.brand)
    if args.check_only:
        print('PASS: isolated public package and checksums; no modifications or upload.')
        return
    local = root/'news-sitemap.xml'
    cleaned, _ = prune(local.read_text(encoding='utf-8'))
    deploy = True
    if args.scheduled == 'true':
        _, live = request('https://'+args.brand+'.com/news-sitemap.xml')
        _, expired = prune(live)
        deploy = expired > 0
    # Validation precedes this one intentional maintenance transformation.
    local.write_text(cleaned, encoding='utf-8')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as stream:
            stream.write('deploy='+str(deploy).lower()+'\n')
    print('PASS: public package validated. Deployment needed:',deploy)

if __name__ == '__main__':
    main()

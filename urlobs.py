#!/usr/bin/env python3
import requests
import yaml
import hashlib
from lxml import etree
from bs4 import BeautifulSoup
import json
import time
import re
import traceback
from argparse import ArgumentParser


def process_content(text):
    # Replace sequences of spaces, tabs, and carriage returns with a single space
    return re.sub(r'[ \t\r]+', ' ', text)

def fetch_content(url, headers=None, post_data=None, verbose=False):
    # Fetch content from URL using GET or POST
    if post_data:
        response = requests.post(url, data=post_data, headers=headers)
    else:
        response = requests.get(url, headers=headers)
    if verbose and not response.ok:
        print(f"failure {response.status_code}: {response.text}")
    response.raise_for_status()
    return response.text

def parse_content(page, content_type, xpath, fn=None):
    # Parse content based on type (HTML, XML, JSON)
    if content_type == "html":
        soup = BeautifulSoup(page, 'html.parser')
        return [ element.get_text() for element in soup.select(xpath) ]
    elif content_type == "xml":
        tree = etree.fromstring(page.encode('utf8'))
        return [ element.text for element in tree.xpath(xpath) ]
    elif content_type == "json":
        data = json.loads(page)
        return eval(fn, {}, {'data': data})
    else:
        raise ValueError(f"Unknown content type: {content_type}")

def main(config='url.yaml', verbose=False):
    with open(config, 'r', encoding='utf-8') as file:
        urls = yaml.safe_load(file)

    for info in urls:
        url = info.get('url')
        if verbose: print(f"processing {url}")
        post_data = info.get('post') # POST data, implies POST request
        xpath = info.get('xpath')
        fn = info.get('fn')
        content_type = info.get('type', 'html')
        title = info.get('title', url)
        hash_value = info.get('hash', '')
        old_content = info.get('content', [])
        freq = info.get('interval', 0)
        last_date = info.get('last', 0)
        keep_old = info.get('keep_old', 0)
        no_order = info.get('no_order', keep_old)
        only_diffs = info.get('onlydiffs', 1)
        failures = info.get('failures', 0)
        user_agent = info.get('user_agent')
        cookie = info.get('cookie')
        content_type_header = info.get('content_type')
        min_alert_failures = info.get('min_failure_alert', 5)

        headers = info.get('headers', {})
        if cookie:
            headers['Cookie'] = cookie
        if content_type_header:
            headers['Content-Type'] = content_type_header
        if user_agent:
            headers['User-Agent'] = user_agent

        freq *= 2 ** min(min_alert_failures, failures)
        now = time.time()
        if last_date + freq > now: # Skip too fresh
            continue

        try:
            if verbose: print(f"fetching {url}, {headers=}")
            page = fetch_content(url, headers=headers, post_data=post_data, verbose=verbose)
            info['last'] = now
            render = parse_content(page, content_type, xpath, fn)
            if keep_old:
                render.extend(( el for el in old_content if el not in render ))
            if no_order:
                render.sort()
            render = [ process_content(el) for el in render ]

            if verbose:
                print(f"old: {old_content}")
                print(f"rendered: {render}")

            new_hash = hashlib.md5(''.join(render).encode('utf-8')).hexdigest()
            if verbose: print(f"hashed: {new_hash}")

            if hash_value != new_hash:
                diffs = []
                if only_diffs:
                    old_set, new_set = set(old_content), set(render)
                    diffs.append("++ New:")
                    diffs.extend(( f"  {el}" for el in new_set - old_set ))
                    diffs.append("-- Off:")
                    diffs.extend(( f"  {el}" for el in old_set - new_set ))
                else:
                    diffs = list(set(old_content) ^ set(render))
                print(f"〉 Changes for {title}:\n" + "\n".join(diffs) + "\n")
            elif verbose:
                print(f"No change for {title}")

            info['hash'] = new_hash
            info['content'] = render
            info['failures'] = 0
        except Exception as e:
            if verbose: traceback.print_exception(e)
            print(f"〉✗ Failure for {title}: {e}")
            info['failures'] += 1
            if failures >= min_alert_failures:
                print(f"〉✗ Alert: Fetch failed for {title} (freq: {freq})")

    with open(config, 'w', encoding='utf-8') as file:
        yaml.safe_dump(urls, file)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('config')
    parser.add_argument('--verbose', default=False, action='store_true')
    args = parser.parse_args()
    if args.verbose: print(f"args: {args}")
    main(**vars(args))

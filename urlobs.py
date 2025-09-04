#!/usr/bin/env python3
import sys, json, yaml, hashlib, time, re, requests, traceback
from lxml import etree
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from urllib.parse import urljoin
from argparse import ArgumentParser


def safe_first(xs):
    if len(xs) == 0: return None
    else: return xs[0]

def process_content(text):
    text = re.sub(r'^ *[-—] *', '', text)
    # Replace sequences of spaces, tabs, and carriage returns with a single space
    text = re.sub(r'[ \t\r]+', ' ', text)
    return text

def escape_chars(input: str, special: str) -> str:
    for char in special:
        input = input.replace(char, f'\\{char}')
    return input

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

@dataclass(frozen=True, order=True)
class Item:
    text: str
    url: str

yaml.add_representer(Item, lambda dumper, data: dumper.represent_dict(asdict(data)),
                     Dumper=yaml.SafeDumper)

class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Item):
            return asdict(obj)
        return super().default(obj)

def parse_content(page, content_type, xpath, xpath_text, xpath_url, fn):
    # Parse content based on type (HTML, XML, JSON)
    if content_type == "html":
        soup = BeautifulSoup(page, 'html.parser')
        def get_text(element):
            if xpath_text and (el := safe_first(element.select(xpath_text))):
                return el.get_text()
            else:
                return element.get_text()
        def get_url(element):
            if xpath_url and (el := safe_first(element.select(xpath_url))):
                if (href := el.get('href') or el.get('src')):
                    return href
                else:
                    return el.get_text()
            elif (href := element.get('href') or element.get('src')):
                return href
            elif (el := element.find(attrs={'href': True}) or element.find(attrs={'src': True})):
                return el.get('href') or el.get('src')
        return [ dict(text=get_text(element), url=get_url(element))
                for element in soup.select(xpath) ]

    elif content_type in ("xml", "rss", "atom"):
        if content_type == 'atom' and 'xmlns' in page[:500]:
            page = re.sub(r'xmlns="[^"]+"', "", page) # F namespaces
        tree = etree.fromstring(page.encode('utf8'))

        def get_text(element):
            if xpath_text and (el := safe_first(element.xpath(xpath_text))) is not None:
                return el.text
            else:
                return element.text
        def get_url(element):
            if xpath_url and (el := safe_first(element.xpath(xpath_url))) is not None:
                if (href := el.get('href') or el.get('src')):
                    return href
                else:
                    return el.text
            elif (href := element.get('href') or element.get('src')):
                return href
            elif (el := element.xpath('*[@href and @href!=""]') or element.xpath('*[@src and @src!=""]')):
                return el.get('href') or el.get('src')
        return [ dict(text=get_text(element), url=get_url(element))
                for element in tree.xpath(xpath) ]

    elif content_type == "json":
        data = json.loads(page)
        xs = eval(fn, {}, {'data': data}) # arbitrary code execution
        return list(xs)

    else:
        raise ValueError(f"Unknown content type: {content_type}")

def main(config='url.yaml', verbose=False, format='text', dry_run=False):
    with open(config, 'r', encoding='utf-8') as file:
        urls = yaml.safe_load(file)

    outputs = {}

    for info in urls:
        url = info.get('url')
        if verbose: print(f"processing {url}")

        content_type = info.get('type', 'html')
        xpath = None
        xpath_text = None
        xpath_url = None
        if content_type == 'rss':
            xpath = '/rss/channel/item'
            xpath_text = './title'
            xpath_url = './link'
        elif content_type == 'atom':
            xpath = '/feed/entry'
            xpath_text = './title'
            xpath_url = './link'

        post_data = info.get('post') # POST data, implies POST request
        xpath = info.get('xpath', xpath)
        xpath_text = info.get('xpath_text', xpath_text)
        xpath_url = info.get('xpath_url', xpath_url)
        fn = info.get('fn')
        title = info.get('title', url)
        hash_value = info.get('hash', '')
        old_items = [ Item(**x) for x in info.get('content', []) ]
        freq = info.get('interval', 0)
        last_date = info.get('last', 0)
        keep_old = info.get('keep_old', 0)
        no_order = info.get('no_order', 0)
        only_diffs = info.get('onlydiffs', 1)
        only_news = info.get('onlynews', 0)
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
            xs = parse_content(page, content_type, xpath, xpath_text, xpath_url, fn)
            items = [ Item(text=process_content(x['text']),
                           url=urljoin(url, x['url'].strip()))
                     for x in xs ]

            if keep_old > 0:
                items.extend([ el
                               for el in old_items
                               if el not in items ][:keep_old])
            if no_order:
                items.sort()

            if verbose:
                print(f"old: {old_items}")
                print(f"rendered: {items}")

            new_hash = hashlib.md5(str(items).encode('utf-8')).hexdigest()
            if verbose: print(f"hashed: {new_hash}")

            if hash_value != new_hash:
                output = {}
                if only_diffs:
                    old_set = set(old_items)
                    new_set = set(items)
                    if (new := new_set - old_set):
                        output['new'] = [ x for x in items if x in new ] # keep order
                    if not only_news and (old := old_set - new_set):
                        output['old'] = [ x for x in items if x in old ] # keep order
                elif (all := list(dict.fromkeys(items))): # dedup
                    output['all'] = all

                if output: # only if not empty
                    outputs[title] = output
            elif verbose:
                print(f"No change for {title}")

            info['hash'] = new_hash
            info['content'] = items
            info['failures'] = 0
        except Exception as e:
            if verbose: traceback.print_exception(e)
            print(f"〉✗ Failure for {title}: {e}")
            info['failures'] = failures = failures + 1
            if failures >= min_alert_failures:
                print(f"〉✗ Alert: Fetch failed for {title} (freq: {freq})")

    # outputs
    if format == 'text':
        for title, output in outputs.items():
                print(f"〉 Changes for {title}:\n")
                def print_them(xs):
                    print('\n'.join(( f"  {x.text}" for x in xs )))
                if (new := output.get('new')):
                    print("++ New:")
                    print_them(new)
                if (old := output.get('old')):
                    print("-- Old:")
                    print_them(old)
                if (all := output.get('all')):
                    print_them(all)

    if format == 'markdown':
        for title, output in outputs.items():
                print(f"# {title}\n")
                def print_them(xs):
                    print('\n'.join(( f"- [{escape_chars(x.text, '[]')}]({escape_chars(x.url, '()')})"
                                     for x in xs )))
                if (new := output.get('new')):
                    print("## New")
                    print_them(new)
                if (old := output.get('old')):
                    print("## Old")
                    print_them(old)
                if (all := output.get('all')):
                    print_them(all)

    elif format == 'json':
        json.dump(outputs, sys.stdout, cls=JsonEncoder)

    elif format == 'yaml':
        yaml.safe_dump(outputs, sys.stdout)

    # write state back to file
    if not dry_run:
        with open(config, 'w', encoding='utf-8') as file:
            yaml.safe_dump(urls, file, sort_keys=False)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('config')
    parser.add_argument('--verbose', default=False, action='store_true')
    parser.add_argument('--format', default='text', choices=('text', 'markdown', 'json', 'yaml'))
    parser.add_argument('--dry-run', default=False, action='store_true')
    args = parser.parse_args()
    if args.verbose: print(f"args: {args}")
    main(**vars(args))

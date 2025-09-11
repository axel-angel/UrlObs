#!/usr/bin/env python3
import sys, yaml, json, argparse, string
from openai import OpenAI
from pydantic import BaseModel, Field
import itertools
D = dict

client = OpenAI()  # Assumes OPENAI_API_KEY env var
DEFAULT_PROMPT = """Take this list of news headlines and make a digest of it: find big categories to group similar items together by thematic.
The input contains the sources then the items: - ref: title
Each item must be: short title then one sentence summary then the reference (ref).
Write to be concise to-the-point, your titles should be keywords or very short.
Ideally we should have {item_count:d} items, put the most important categories first.
Feel free to filter out non-news items (like reporting/asking questions/bug issues).
Make sure there are no duplicates and each item/reference only appears once.
The output format must be JSON."""


def escape_chars(input: str, special: str) -> str:
    for char in special:
        input = input.replace(char, f'\\{char}')
    return input

def escape_md(input: str) -> str:
    return escape_chars(x, '{}[]\n\r\t')

def convert(xs):
    assert len(xs) <= 26

    next_ref = itertools.count(start=1).__next__
    def go(letter, idx, *, text, url):
        return D(text=text,
                 url=url,
                 ref=next_ref(),
             )
    return [ D(source=title,
               articles=[ go(letter, idx, **article)
                         for idx, article in enumerate(articles, 1) ])
            for feed_counter, (title, x) in enumerate(xs.items())
            if (articles := x.get('new'))
            # TODO: Handle >26 feeds
            if (letter := string.ascii_uppercase[feed_counter % 26]) ]


class DigestItem(BaseModel):
    title: str
    summary: str
    refs: list[int]

class DigestCategory(BaseModel):
    name: str
    items: list[DigestItem]

class NewsDigest(BaseModel):
    categories: list[DigestCategory]


def main(*, input_yaml, prompt, model, temperature, item_count, output_fd):
    # prepare data and make prompt
    with open(input_yaml, 'r') as fd:
        xs = yaml.safe_load(fd)
    if not xs:
        print(f"Input diff file is empty. Aborting")
        exit(1)

    ys = convert(xs)

    prompt = f"""{prompt.format(item_count=item_count)}
Articles:\n
```json
{json.dumps(ys)}
```"""

    completion = client.beta.chat.completions.parse(
        model=model,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
        response_format=NewsDigest,
    )
    digest = completion.choices[0].message.parsed

    # print AI reply
    output_fd.write("# Digest\n")
    for category in digest.categories:
        output_fd.write(f"## {category.name}\n")
        for item in category.items:
            refs_str = ''.join(( f"[^{ref}]" for ref in item.refs ))
            output_fd.write(f"- **{item.title}**: {item.summary}{refs_str}\n")
        output_fd.write("\n")
    output_fd.write("\n")

    # print all references
    output_fd.write("# Sources\n")
    for y in ys:
        for z in y['articles']:
            output_fd.write(f"[^{z['ref']}]: {y['source']}: [{escape_md(z['text'])}]({escape_md(z['url'])})\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate article digest using GPT-4")
    parser.add_argument("input_yaml", help="YAML file with feed data")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Custom prompt for GPT")
    parser.add_argument("--model", default='gpt-4o', help="OpenAI model to use")
    parser.add_argument("--temperature", default=0.2, type=float, help="Model temperature")
    parser.add_argument("--output", default=None, help="File to write output to")
    parser.add_argument("--item_count", default=25, type=int)
    args = parser.parse_args()

    if args.output is None:
        args.output_fd = sys.stdout
    else:
        args.output_fd = open(args.output, 'wt')
    del args.output

    main(**vars(args))
    args.output_fd.close()

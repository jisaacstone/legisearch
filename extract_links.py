#!/usr/bin/env python3

from html.parser import HTMLParser


BASEURL='https://mountainview.legistar.com'


class HREFParser(HTMLParser):
    def __init__(self, search_str):
        super(HREFParser, self).__init__()
        self.search_str = search_str
        self.found = []

    def handle_starttag(self, tag, attrs_):
        if tag == 'a':
            attrs = dict(attrs_)
            if 'href' in attrs:
                if self.search_str in attrs['href']:
                    self.found.append(attrs['href'])


if __name__ == '__main__':
    import sys
    fn = sys.argv[1]
    # M=M: minutes, M=A: agenda, M=I: invite.ics
    parser = HREFParser('M=M')
    with open(fn) as fob:
        parser.feed(fob.read())
    for href in parser.found:
        print(f'{BASEURL}/{href}')

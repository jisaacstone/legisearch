#!/usr/bin/env python3

# Note: this requires tesseract, pytesseract and pdf2image

import re
from pathlib import Path
import pytesseract
import pdf2image

BASEURL='https://mountainview.legistar.com/'
METASEP='-=-=-\n'
# OCR tries to interpret bider holes as text
linestartfunk = re.compile(r'^\W?\s', re.MULTILINE)
lineendfunk = re.compile(r'\s\W$|[ 	]$', re.MULTILINE)
header1 = re.compile(
    r'(^[\w\\]+ .{,50})^(\w+ \d\d?, \d\d\d\d).{,4}page \d\d? of \d\d?',
    re.MULTILINE | re.IGNORECASE | re.DOTALL
)

header2 = re.compile(r'^([A-Za-z\\/ ]+[a-z]) ([A-Z ]+) .*(\d\d?/\d\d?/\d\d\d\d)')
footer = re.compile(r'city of mountain view page \d+$', re.IGNORECASE)

def ocr_all():
    base = Path('minutes')
    out = Path('ocr_minutes')
    for year in base.iterdir():
        out2 = out / year.name
        out2.mkdir(parents=True, exist_ok=True)
        for file in year.iterdir():
            if file.suffix != '.pdf' or not file.is_file():
                continue
            txt = out2 / (file.stem + '.txt')
            if not txt.exists():
                ocr_file(file, txt)
            break

def ocr_file(pdf_file, txt_file):
    images = pdf2image.convert_from_path(pdf_file)
    with open(txt_file, 'w') as fob:
        metadata = {'link': BASEURL + pdf_file.stem}
        for image in images:
            # psm 6 assumes no tabular data
            page_text = pytesseract.image_to_string(image, config='--psm 6')
            cleaned_text = cleanup(page_text, metadata)
            fob.write(cleaned_text)
        write_metadata(fob, metadata)
    print(txt_file, 'written')


def cleanup(text, metadata):
    subbed = re.sub(
        lineendfunk, '', re.sub(linestartfunk, '', text)
    )
    header_split = re.split(header1, subbed, maxsplit=1)
    if len(header_split) > 1:
        if not metadata.get('date'):
            metadata['date'] = header_split[2]
            metadata['doctype'] = header_split[1]
        return header_split[-1]
    match = header2.match(subbed)
    if match:
        if not metadata.get('date'):
            metadata['date'] = match.group(3)
            metadata['doctype'] = match.group(2)
            metadata['body'] = match.group(1)
        subbed = subbed[match.end():]
    return footer.sub('', subbed)


def write_metadata(fob, metadata):
    fob.write(METASEP)
    for k, v in sorted(metadata.items()):
        fob.write(f'{k}: {v.strip()}\n')


if __name__ == '__main__':
    ocr_all()
    #in_ = Path('minutes/2013-city-council/M=M&ID=282072&GUID=0DF3E8BD-5800-47D6-B55F-0912038E110A.pdf')
    #out_ = Path('ocr_minutes/2013-city-council/M=M&ID=282072&GUID=0DF3E8BD-5800-47D6-B55F-0912038E110A.txt')
    #ocr_file(in_, out_)

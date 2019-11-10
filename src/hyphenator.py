#!/usr/bin/env python3
# coding: utf-8
# SPDX-License-Identifier: Apache-2.0


# Copyright 2019 AntiCompositeNumber

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import requests
import mwparserfromhell
from stdnum import isbn


def get_wikitext(url):
    if '?' in url:
        wikitext_url = url + '&action=raw'
    else:
        wikitext_url = url + '?action=raw'

    headers = {'user-agent': 'anticompositetools/hyphenator '
               '(https://tools.wmflabs.org/anticompositetools/hyphenator; '
               'tools.anticompositetools@tools.wmflabs.org) python-requests/'
               + requests.__version__}

    for i in range(1, 5):
        try:
            request = requests.get(wikitext_url, headers=headers)
            request.raise_for_status()
        except Exception:
            time.sleep(5)
            continue
        else:
            start_time = time.strftime('%Y%m%d%H%M%S', time.gmtime())
            break

    timestruct = time.strptime(request.headers['Last-Modified'],
                               '%a, %d %b %Y %H:%M:%S %Z')
    edit_time = time.strftime('%Y%m%d%H%M%S', timestruct)

    return (request.text, (edit_time, start_time))


def find_isbns(code):
    for template in code.ifilter_templates():
        if template.name.matches('ISBN') or template.name.matches('ISBNT'):
            try:
                raw_isbn = template.get('1').value
            except ValueError:
                continue
            para = '1'

        elif template.has('isbn', ignore_empty=True):
            raw_isbn = template.get('isbn').value
            para = 'isbn'
        elif template.has('ISBN', ignore_empty=True):
            raw_isbn = template.get('ISBN').value
            para = 'ISBN'
        else:
            continue

        yield (template, raw_isbn, para)


def check_isbn(raw_isbn):
    """If the ISBN can be worked on, return True"""
    if len(raw_isbn) == 17 or not isbn.is_valid(raw_isbn):
        return False
    else:
        return True


def main(url):
    try:
        wikitext, times = get_wikitext(url)
    except Exception as err:
        return err, ('', ''), 0

    code = mwparserfromhell.parse(wikitext)
    count = 0
    for template, raw_isbn, para in find_isbns(code):
        if not check_isbn(raw_isbn):
            continue

        new_isbn = isbn.format(raw_isbn, convert=True)
        if raw_isbn != new_isbn:
            count += 1
            template.add(para, new_isbn)

    return code, times, count


if __name__ == '__main__':
    main()

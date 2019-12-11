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
import urllib.parse
import requests
import mwparserfromhell
from stdnum import isbn
import flask

bp = flask.Blueprint('hyphenator', __name__, url_prefix='/hyphenator')
flash = []


def get_wikitext(url):
    wikitext_url = url + '&action=raw'

    headers = {'user-agent': 'anticompositetools/hyphenator '
               '(https://tools.wmflabs.org/anticompositetools/hyphenator; '
               'tools.anticompositetools@tools.wmflabs.org) python-requests/'
               + requests.__version__}

    for i in range(1, 5):
        try:
            request = requests.get(wikitext_url, headers=headers)
            request.raise_for_status()
        except Exception:
            if request.status_code == 404:
                flash.append(('That page does not exist.', 'danger'))
                raise
            else:
                time.sleep(5)
                continue
        else:
            start_time = time.strftime('%Y%m%d%H%M%S', time.gmtime())
            timestruct = time.strptime(request.headers['Last-Modified'],
                                       '%a, %d %b %Y %H:%M:%S %Z')
            edit_time = time.strftime('%Y%m%d%H%M%S', timestruct)
            return (request.text, (edit_time, start_time))


def find_isbns(code):
    for template in code.ifilter_templates():
        if template.name.matches('ISBN') or template.name.matches('ISBNT'):
            try:
                raw_isbn = template.get('1').value.strip()
            except ValueError:
                continue
            para = '1'

        elif template.has('isbn', ignore_empty=True):
            raw_isbn = template.get('isbn').value.strip()
            para = 'isbn'
        elif template.has('ISBN', ignore_empty=True):
            raw_isbn = template.get('ISBN').value.strip()
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


def get_page_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.path == '/w/index.php':
        query_params = urllib.parse.parse_qs(parsed.query)
        if 'oldid' not in query_params:
            title = query_params['title'][0]
        else:
            flash.append(('Invalid URL', 'danger'))
            raise ValueError  # fix
    elif '/wiki/' in parsed.path:
        title = parsed.path[6:]
    else:
        flash.append(('Invalid URL', 'danger'))
        raise ValueError  # this one too

    new_url = (parsed.scheme + '://' + parsed.netloc
               + '/w/index.php?title=' + title)
    return new_url


def main(raw_url):
    url = get_page_url(raw_url)
    wikitext, times = get_wikitext(url)

    code = mwparserfromhell.parse(wikitext)
    count = 0
    for template, raw_isbn, para in find_isbns(code):
        if not check_isbn(raw_isbn):
            continue

        new_isbn = isbn.format(raw_isbn, convert=True)
        if raw_isbn != new_isbn:
            count += 1
            template.add(para, new_isbn)

    return code, times, count, url


@bp.route('/', methods=['GET'])
def form():
    return flask.render_template('hyphenator-form.html')


@bp.route('/output', methods=['POST'])
def output():
    def check_err(messages):
        for message in messages:
            if message[1] == 'danger':
                return True
        return False

    if flask.request.method == 'POST':
        pageurl = flask.request.form['page_url']
        try:
            newtext, times, count, url = main(pageurl)
        except Exception as err:
            if not check_err(flash):
                flash.append((
                    'An unhandled {0} exception occurred.'.format(err),
                    'danger'))

            for message in flash:
                flask.flash(message[0], message[1])

            return flask.redirect(flask.url_for('hyphenator.form'))

        submit_url = url + '&action=submit'

        return flask.render_template(
                'hyphenator-output.html', count=count,
                submit_url=submit_url, newtext=newtext, edit_time=times[0],
                start_time=times[1])

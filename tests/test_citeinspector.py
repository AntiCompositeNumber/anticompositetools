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

import pytest
import requests
import mwparserfromhell as mwph
import src.citeinspector as citeinspector


def test_get_page_url():
    page = 'User:AntiCompositeNumber/test_anticompositetools'
    url = ('https://en.wikipedia.org/w/index.php?'
           'title=User:AntiCompositeNumber/test_anticompositetools')
    assert citeinspector.get_page_url(page) == url


def test_get_wikitext():
    url = ('https://en.wikipedia.org/w/index.php?'
           'title=User:AntiCompositeNumber/test_anticompositetools')

    s = requests.Session()
    wikitext, (edit_time, start_time) = citeinspector.get_wikitext(url, s)

    with open('tests/testdata.txt') as f:
        assert wikitext == f.read()

    assert edit_time
    assert start_time


def test_get_wikitext_notfound():
    url = ('https://en.wikipedia.org/w/index.php?'
           'title=User:AntiCompositeNumber/test_anticompositetools/'
           'ee8f300b-f058-4222-ac69-86ab735ba450')

    s = requests.Session()
    with pytest.raises(citeinspector.HandledError):
        wikitext, (edit_time, start_time) = citeinspector.get_wikitext(url, s)


def test_get_citoid_template_types():
    s = requests.Session()
    template_type_map, supported_templates = \
        citeinspector.get_citoid_template_types(s)

    assert type(template_type_map) is dict
    assert type(supported_templates) is list
    assert template_type_map.get('webpage') == 'Cite web'
    assert template_type_map.get('book') == 'Cite book'
    assert template_type_map.get('journalArticle') == 'Cite journal'
    assert template_type_map.get('newspaperArticle') == 'Cite news'

    for item in ['Cite web', 'Cite book', 'Cite journal', 'Cite news']:
        assert item in supported_templates


def test_find_refs():
    with open('tests/testdata.txt') as f:
        text = f.read()

    code = mwph.parse(text)
    refs = list(citeinspector.find_refs(code, ['Cite book']))

    assert len(refs) == 2


def test_get_bib_ident_isbn():
    data = {'data': {'edition': 'Newition',
                     'isbn': '9781786751041 ',
                     'title': "Alice's adventures in Wonderland "},
            'location': 'ref',
            'name': 'fcabdd30-69ab-4a76-896d-982a4d61f6ca',
            'source': 'wikitext',
            'template': 'Cite book',
            'wikitext': ('<ref>{{cite book '
                         "|title=Alice's adventures in Wonderland "
                         '|isbn=9781786751041 |edition=Newition}}</ref>')}

    ident = citeinspector.get_bib_ident(data)
    assert ident.strip() == '9781786751041'


def test_lastnamefirstname_seperate():
    author = ['George', 'Washington']
    last, first = citeinspector.lastnamefirstname(author)
    assert last == 'Washington'
    assert first == 'George'


def test_lastnamefirstname_commas_lifespan():
    author = ['', 'Twain, Mark, 1835-1910']
    last, first = citeinspector.lastnamefirstname(author)
    assert last == 'Twain'
    assert first == 'Mark'


def test_lastnamefirstname_commas_nodate():
    author = ['', 'Washington, George,']
    last, first = citeinspector.lastnamefirstname(author)
    assert last == 'Washington'
    assert first == 'George'


def test_lastnamefirstname_blank():
    author = ['', '']
    last, first = citeinspector.lastnamefirstname(author)
    assert last is None
    assert first is None


def test_lastnamefirstname_one():
    author = ['', 'Jimbo']
    last, first = citeinspector.lastnamefirstname(author)
    assert not first
    assert last == 'Jimbo'

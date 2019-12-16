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
import unittest.mock as mock
import sys
import os
sys.path.append(os.path.realpath(os.path.dirname(__file__)+"/.."))
import src.citeinspector as citeinspector  # noqa: E402
import src  # noqa: E402


@pytest.fixture
def client():
    conf = {'secret_key': 'TestTest',
            'TESTING': True}
    app = src.create_app(test_config=conf)

    with app.test_client() as test_client:
        yield test_client


def test_get_page_url_page():
    page = 'User:AntiCompositeNumber/test_anticompositetools'
    url = ('https://en.wikipedia.org/w/index.php?'
           'title=User:AntiCompositeNumber/test_anticompositetools')
    out = citeinspector.get_page_url(page)
    assert out[0] == url
    assert out[1] == page


def test_get_page_url_wiki():
    input_url = ('https://en.wikipedia.org/wiki/'
                 'User:AntiCompositeNumber/test_anticompositetools')
    url = ('https://en.wikipedia.org/w/index.php?'
           'title=User:AntiCompositeNumber/test_anticompositetools')

    assert citeinspector.get_page_url(input_url)[0] == url


def test_get_page_url_w():
    input_url = ('https://en.wikipedia.org/w/index.php?'
                 'title=User:AntiCompositeNumber/test_anticompositetools')
    url = ('https://en.wikipedia.org/w/index.php?'
           'title=User:AntiCompositeNumber/test_anticompositetools')

    assert citeinspector.get_page_url(input_url)[0] == url


def test_get_page_url_notitle():
    input_url = ('https://en.wikipedia.org/w/index.php'
                 '?title=User:AntiCompositeNumber/test_anticompositetools'
                 '&diff=930066511&oldid=927923634&diffmode=source')
    with pytest.raises(ValueError):
        citeinspector.get_page_url(input_url)


def test_get_page_url_nonwiki():
    input_url = 'http://example.com'
    with pytest.raises(ValueError):
        citeinspector.get_page_url(input_url)


def test_get_page_url_malformed():
    input_url = ('https://en.wikipedia.org/'
                 'User:AntiCompositeNumber/test_anticompositetools')
    with pytest.raises(ValueError):
        citeinspector.get_page_url(input_url)


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


def test_find_refs_blank():
    code = mwph.parse('')
    refs = list(citeinspector.find_refs(code, ['Cite book']))
    assert len(refs) == 0


def test_find_refs_notemplate():
    code = mwph.parse('<ref>Smith, John</ref>')
    refs = list(citeinspector.find_refs(code, ['Cite book']))
    assert len(refs) == 0


def test_find_refs_wrongtemplate():
    code = mwph.parse('<ref>{{Example|title=Title}}</ref>')
    refs = list(citeinspector.find_refs(code, ['Cite book']))
    assert len(refs) == 0


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


def test_concat_items():
    wikitext_data = {
        'data': {
            'last1': 'Ipsum',
            'first1': 'Lorem',
            'access-date': '2019-12-31',
            'isbn': '9781786751041'
            },
        'name': 'name',
        'template': 'Cite book',
        'location': 'ref',
        'wikitext': 'foo'
        }

    citoid_data = {
        'data': {
            'last': 'Ipsum',
            'first': 'Lorem',
            'title': 'Foo Bar'
            },
        'template': 'Cite book',
        'source': 'WorldCat',
        'template_data': {
            'params': {
                'last': {'aliases': ['author', 'last1']},
                'first': {'aliases': ['first1']},
                'title': {},
                # isbn ommitted
                'access-date': {}
                }
            }
        }

    concat_data = {
        'name': 'name',
        'template': 'Cite book',
        'citoid_source': 'WorldCat',
        'location': 'ref',
        'data': {
            'last1': {
                'wikitext': 'Ipsum',
                'citoid': 'Ipsum',
                'ratio': 100
                },
            'first1': {
                'wikitext': 'Lorem',
                'citoid': 'Lorem',
                'ratio': 100
                },
            'title': {
                'wikitext': '',
                'citoid': 'Foo Bar',
                'ratio': 0
                },
            'isbn': {
                'wikitext': '9781786751041',
                'citoid': '',
                'ratio': 0
                }
            },
        'wikitext': 'foo'
        }

    cite = citeinspector.concat_items(wikitext_data, citoid_data)

    for key, value in concat_data.items():
        assert cite.get(key) == value

    assert not cite.get('access-date')


def test_concat_items_badtemplate():
    wikitext_data = {
        'data': {},
        'name': 'name',
        'template': 'Cite web',
        }

    citoid_data = {
        'data': {},
        'template': 'Cite book',
        }

    cite = citeinspector.concat_items(wikitext_data, citoid_data)
    assert cite is None


def test_fuzz_item():
    assert citeinspector.fuzz_item('The Quick Brown Fox',
                                   'The Fantastic Mr. Fox') == 53


def test_fuzz_seq():
    lista = ['The', 'Quick', 'Brown', 'Fox']
    listb = ['The', 'Fantastic', 'Mr.', 'Fox']
    assert citeinspector.fuzz_seq(lista, listb) == 56


def test_get_parsoid_data_isbn():
    s = requests.Session()
    ident = '9781786751041'
    data = citeinspector.get_parsoid_data(ident, s)
    citedata = {'ISBN': ['978-1-78675-104-1', '1-78675-104-6'],
                'author': [['', 'Carroll, Lewis, 1832-1898,']],
                'contributor': [['', 'Ingpen, Robert, 1936-']],
                'edition': 'New edition',
                'itemType': 'book',
                'numPages': '1 volume',
                'oclc': '1063566503',
                'place': 'London',
                'source': ['WorldCat'],
                'title': "Alice's adventures in Wonderland",
                'url': 'https://www.worldcat.org/oclc/1063566503'}
    data.pop('accessDate', None)
    assert data
    assert data == citedata


def test_get_parsoid_data_invalid_ident():
    s = requests.Session()
    ident = 'DefinitelyLegitimateReference'
    data = citeinspector.get_parsoid_data(ident, s)
    assert data is None


def test_map_parsoid_to_templates():
    raw_parsoid_data = {
        'ISBN': ['978-1-78675-104-1', '1-78675-104-6'],
        'author': [
            ['', 'Carroll, Lewis, 1832-1898,'],
            ['', 'Ipsum, Lorem, 1970,']
            ],
        'editor': [
            ['Dolor', 'Sit'],
            ['Foo', 'Bar']
            ],
        'itemType': 'book',
        'source': ['WorldCat'],
        'title': "Alice's adventures in Wonderland"}
    wikitext_data = {
        'location': 'ref',
        'name': 'fcabdd30-69ab-4a76-896d-982a4d61f6ca'}
    template_data_cache = {}
    template_type_map = {'book': 'Cite book'}
    session = requests.Session()

    citoid_data, new_td_cache = citeinspector.map_parsoid_to_templates(
            raw_parsoid_data, wikitext_data, template_data_cache,
            template_type_map, session)

    assert type(citoid_data) is dict
    assert citoid_data['template'] == 'Cite book'
    assert citoid_data['source'] == 'WorldCat'

    citedata = citoid_data['data']
    assert citedata['last'] == 'Carroll'
    assert citedata['first'] == 'Lewis'
    assert citedata['last2'] == 'Ipsum'
    assert citedata['first2'] == 'Lorem'
    assert citedata['editor-last'] == 'Sit'
    assert citedata['editor-first'] == 'Dolor'
    assert citedata['editor2-last'] == 'Bar'
    assert citedata['editor2-first'] == 'Foo'
    assert citedata['title'] == "Alice's adventures in Wonderland"


def test_map_parsoid_to_templates_notemplate():
    raw_parsoid_data = {'itemType': 'magazine'}
    wikitext_data = {}
    templatedata_cache = {}
    template_type_map = {'book': 'Cite book'}
    session = requests.Session()

    citoid_data, new_td_cache = citeinspector.map_parsoid_to_templates(
            raw_parsoid_data, wikitext_data, templatedata_cache,
            template_type_map, session)

    assert citoid_data is None
    assert new_td_cache == templatedata_cache


def test_get_TemplateData_map():
    session = requests.Session()
    template = 'Cite web'
    data = citeinspector.get_TemplateData_map(template, session)
    assert data.get('maps').get('citoid')
    assert type(data.get('maps').get('citoid')) is dict
    assert data.get('paramOrder')
    assert type(data.get('paramOrder')) is list
    assert data.get('title') == 'Template:Cite web'


def test_get_retry_servererr():
    s = mock.MagicMock()
    response = mock.MagicMock()
    response.raise_for_status.side_effect = Exception('internal server error')
    response.status_code == 500
    response.text = ''
    mock_sleep = mock.MagicMock()
    s.get.return_value = response

    with mock.patch('time.sleep', mock_sleep):
        with pytest.raises(Exception):
            citeinspector.get_retry('http://example.com', s)

    assert mock_sleep.mock_calls == [
        mock.call(5), mock.call(10), mock.call(15)]
    assert s.get.call_count == 4


def test_get_retry_badmethod():
    with pytest.raises(NotImplementedError):
        citeinspector.get_retry('http://example.com', requests.Session(),
                                method='delete')


def test_citeinspector():
    url = ('https://en.wikipedia.org/w/index.php?'
           'title=User:AntiCompositeNumber/test_anticompositetools')
    output, wikitext, meta = citeinspector.citeinspector(url)

    with open('tests/testdata.txt') as f:
        assert f.read() == wikitext

    assert 'not_found' not in meta
    for key in ['start_time', 'edit_time']:
        assert key in meta

    assert output
    assert len(output) == 2


def test_citeinspector_reffail():
    m = mock.MagicMock()
    with open('tests/testdata.txt') as f:
        m.return_value = (f.read(), ('', ''))
    ident = mock.MagicMock()
    ident.return_value = []
    with mock.patch('src.citeinspector.get_wikitext', m):
        with mock.patch('src.citeinspector.find_refs', ident):
            output, wikitext, meta = citeinspector.citeinspector('')

    assert wikitext
    assert not output
    assert meta['not_found'] == 'refs'


def test_citeinspector_identfail():
    m = mock.MagicMock()
    with open('tests/testdata.txt') as f:
        m.return_value = (f.read(), ('', ''))
    ident = mock.MagicMock()
    ident.return_value = None
    with mock.patch('src.citeinspector.get_wikitext', m):
        with mock.patch('src.citeinspector.get_bib_ident', ident):
            output, wikitext, meta = citeinspector.citeinspector('')

    assert wikitext
    assert not output
    assert meta['not_found'] == 'ident'


def test_citeinspector_citoidfail():
    m = mock.MagicMock()
    with open('tests/testdata.txt') as f:
        m.return_value = (f.read(), ('', ''))
    ident = mock.MagicMock()
    ident.return_value = None
    with mock.patch('src.citeinspector.get_wikitext', m):
        with mock.patch('src.citeinspector.get_parsoid_data', ident):
            output, wikitext, meta = citeinspector.citeinspector('')

    assert wikitext
    assert not output
    assert meta['not_found'] == 'data'


def test_citeinspector_concatfail():
    m = mock.MagicMock()
    with open('tests/testdata.txt') as f:
        m.return_value = (f.read(), ('', ''))
    ident = mock.MagicMock()
    ident.return_value = None
    with mock.patch('src.citeinspector.get_wikitext', m):
        with mock.patch('src.citeinspector.concat_items', ident):
            output, wikitext, meta = citeinspector.citeinspector('')

    assert wikitext
    assert not output
    assert meta['not_found'] == 'para'


def test_form(client):
    response = client.get('/citeinspector/')
    assert response.status_code == 200
    assert response.data


def test_output(client):
    form = {'page_url': 'User:AntiCompositeNumber/test_anticompositetools'}
    response = client.post('/citeinspector/output', data=form)

    assert response.status_code == 200
    assert response.data


def test_output_none(client):
    form = {'page_url': 'User:AntiCompositeNumber'}
    response = client.post('/citeinspector/output', data=form)

    assert response.status_code == 404
    assert response.data
    assert b'CS1' in response.data

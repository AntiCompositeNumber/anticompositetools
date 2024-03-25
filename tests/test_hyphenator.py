#!/usr/bin/env python3
# coding: utf-8
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright 2019 AntiCompositeNumber

import pytest
import requests
import mwparserfromhell as mwph
import unittest.mock as mock
import sys
import os

sys.path.append(os.path.realpath(os.path.dirname(__file__) + "/.."))
import src.hyphenator as hyphenator  # noqa: E402


def test_check_isbn_ten():
    isbn = "0486821951"
    assert hyphenator.check_isbn(isbn)


def test_check_isbn_hyphen10():
    isbn = "0-486-82195-1"
    assert hyphenator.check_isbn(isbn)


def test_check_isbn_13():
    isbn = "9780393020397"
    assert hyphenator.check_isbn(isbn)


def test_check_isbn_hyphen13():
    isbn = "978-0-393-02039-7"
    assert not hyphenator.check_isbn(isbn)


def test_check_isbn_invalid():
    isbn = "9780393020390"
    assert not hyphenator.check_isbn(isbn)


def test_check_isbn_notIsbn():
    isbn = "0118999"
    assert not hyphenator.check_isbn(isbn)


def test_get_wikitext_servererr():
    s = mock.MagicMock()
    response = mock.MagicMock()
    response.raise_for_status.side_effect = Exception("internal server error")
    response.status_code == 500
    response.text = ""
    mock_sleep = mock.MagicMock()
    s.get.return_value = response

    with mock.patch("time.sleep", mock_sleep):
        with mock.patch("requests.get", s.get):
            with pytest.raises(Exception):
                hyphenator.get_wikitext("http://example.com")

    assert mock_sleep.mock_calls == [mock.call(5), mock.call(10), mock.call(15)]
    assert s.get.call_count == 4


def test_get_wikitext():
    url = (
        "https://en.wikipedia.org/w/index.php?"
        "title=User:AntiCompositeNumber/test_anticompositetools"
    )

    wikitext, (edit_time, start_time) = hyphenator.get_wikitext(url)

    with open("tests/testdata.txt") as f:
        assert wikitext == f.read()

    assert edit_time
    assert start_time


def test_get_wikitext_notfound():
    url = (
        "https://en.wikipedia.org/w/index.php?"
        "title=User:AntiCompositeNumber/test_anticompositetools/"
        "ee8f300b-f058-4222-ac69-86ab735ba450"
    )

    with pytest.raises(requests.exceptions.HTTPError):
        wikitext, (edit_time, start_time) = hyphenator.get_wikitext(url)


def test_find_isbns():
    with open("tests/testdata.txt") as f:
        wikitext = f.read()

    code = mwph.parse(wikitext)
    sample = [
        ("{{ISBN|0486821951}}", "0486821951", "1"),
        (
            "{{cite book |title=Alice's adventures in Wonderland "
            "|isbn=9781786751041 |edition=Newition}}",
            "9781786751041",
            "isbn",
        ),
        (
            "{{cite book |title=The annotated Huckleberry Finn : "
            "Adventures of Huckleberry Finn (Tom Sawyer's comrade) "
            "|publisher=Norton |ISBN=9780393020397}}",
            "9780393020397",
            "ISBN",
        ),
        ("{{ISBNT|1402714602}}", "1402714602", "1"),
    ]
    assert list(hyphenator.find_isbns(code)) == sample


def test_find_isbns_wrong_template():
    code = mwph.parse("{{ example |title=Fooville }}")
    assert len(list(hyphenator.find_isbns(code))) == 0


def test_find_isbns_bad_template():
    code = mwph.parse("{{ISBN}}")
    assert len(list(hyphenator.find_isbns(code))) == 0


def test_get_page_url_wiki():
    input_url = (
        "https://en.wikipedia.org/wiki/"
        "User:AntiCompositeNumber/test_anticompositetools"
    )
    url = (
        "https://en.wikipedia.org/w/index.php?"
        "title=User:AntiCompositeNumber/test_anticompositetools"
    )

    assert hyphenator.get_page_url(input_url) == url


def test_get_page_url_w():
    input_url = (
        "https://en.wikipedia.org/w/index.php?"
        "title=User:AntiCompositeNumber/test_anticompositetools"
    )
    url = (
        "https://en.wikipedia.org/w/index.php?"
        "title=User:AntiCompositeNumber/test_anticompositetools"
    )

    assert hyphenator.get_page_url(input_url) == url


def test_get_page_url_notitle():
    input_url = (
        "https://en.wikipedia.org/w/index.php"
        "?title=User:AntiCompositeNumber/test_anticompositetools"
        "&diff=930066511&oldid=927923634&diffmode=source"
    )
    with pytest.raises(ValueError):
        hyphenator.get_page_url(input_url)


def test_get_page_url_nonwiki():
    input_url = "http://example.com"
    with pytest.raises(ValueError):
        hyphenator.get_page_url(input_url)


def test_get_page_url_malformed():
    input_url = (
        "https://en.wikipedia.org/" "User:AntiCompositeNumber/test_anticompositetools"
    )
    with pytest.raises(ValueError):
        hyphenator.get_page_url(input_url)

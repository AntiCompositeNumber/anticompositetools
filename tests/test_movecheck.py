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
# import requests
# import mwparserfromhell as mwph
import unittest.mock as mock
import pywikibot
import inspect
import sys
import os
sys.path.append(os.path.realpath(os.path.dirname(__file__)+"/.."))
import src.movecheck as movecheck  # noqa: E402
import src  # noqa: E402


@pytest.fixture
def client():
    m = mock.Mock()
    n = mock.Mock()
    m.return_value = {'secret_key': 'Test'}
    with mock.patch('json.load', m):
        with mock.patch('builtins.open', n):
            app = src.create_app()

    with app.test_client() as test_client:
        yield test_client


@pytest.fixture(scope='module')
def site():
    site = pywikibot.Site('en', 'wikipedia')
    return site


def test_get_AFC_reviewers(site):
    reviewers = movecheck.get_AFC_reviewers(site)
    assert len(reviewers) > 900
    assert type(reviewers) is set


def test_gen_recent_moves(site):
    gen = movecheck.gen_recent_moves(site)
    assert inspect.isgenerator(gen)
    assert type(next(gen)) is pywikibot.logentries.MoveEntry


def test_check_deletions_deleted(site):
    page = pywikibot.Page(site, 'Draft:Calcus Technologies')
    assert movecheck.check_deletions(page, site)


def test_check_deletions_ignored(site):
    page = pywikibot.Page(site, 'Draft:NuWave, LL')
    assert not movecheck.check_deletions(page, site)


def test_check_deletions_never_existed(site):
    page = pywikibot.Page(
        site, 'User:AntiCompositeNumber/test_anticompositetools/'
        '64e65aeb-9dcd-435b-9640-fd3bacf366cc')
    assert not movecheck.check_deletions(page, site)


def test_check_deletions_never_deleted(site):
    page = pywikibot.Page(
        site, 'User:AntiCompositeNumber/test_anticompositetools')
    assert not movecheck.check_deletions(page, site)


def test_check_now_deleted_deleted(site):
    page = pywikibot.Page(site, 'Draft:Calcus Technologies')
    assert movecheck.check_now_deleted(page)


def test_check_now_deleted_live(site):
    page = pywikibot.Page(
        site, 'User:AntiCompositeNumber/test_anticompositetools')
    assert not movecheck.check_now_deleted(page)


def test_check_declines_declined(site):
    page = pywikibot.Page(site, 'Carmen Gentile')
    assert movecheck.check_declines(page)


def test_check_declines_not_declined(site):
    page = pywikibot.Page(
        site, 'User:AntiCompositeNumber/test_anticompositetools')
    assert not movecheck.check_declines(page)


@pytest.mark.skip()
def test_check_declines_rejected():
    raise NotImplementedError


def test_log_metadata(site):
    event = next(movecheck.gen_recent_moves(site))
    data = movecheck.log_metadata(site, event)
    keys = {'title', 'old_title', 'url', 'old_url', 'timestamp', 'user',
            'user_url', 'user_talk_url', 'user_contribs_url', 'comment'}
    assert type(data) is dict
    for key, value in data.items():
        assert type(value) is str

    for key in keys:
        assert key in data


def test_iter_suspicious_moves():
    limit = 3
    data = movecheck.iter_suspicious_moves(limit)
    assert inspect.isgenerator(data)
    ldata = list(data)
    assert len(ldata) == limit
    for item in ldata:
        assert type(item) is dict
        assert type(item['tags']) is list
        assert len(item['tags']) > 0

        for tag in item['tags']:
            assert type(tag) is str
            assert tag


def test_iter_suspicious_moves_tags():
    m = mock.Mock()
    m.return_value = True
    with mock.patch('src.movecheck.check_deletions', m):
        with mock.patch('src.movecheck.check_declines', m):
            data = next(movecheck.iter_suspicious_moves(1))

    for key in ['non-AfC-move', 'previous-ns0-del', 'previous-draft-del',
                'previous-afc-decline']:
        assert key in data['tags']


def test_iter_suspicious_moves_reviewers():
    m = mock.MagicMock()
    move = mock.MagicMock()
    move.user.return_value = 'AntiCompositeNumber'
    m.return_value = [move]
    with mock.patch('src.movecheck.gen_recent_moves', m):
        with pytest.raises(StopIteration):
            next(movecheck.iter_suspicious_moves(1))


def test_movecheck(client):
    limit = 3
    response = client.get('/movecheck?limit=' + str(limit))
    assert response.data.count(b'logitem') == limit


def test_movecheck_default(client):
    response = client.get('/movecheck')
    assert response.data.count(b'logitem') == 20


def test_movecheck_limits_zero(client):
    n = mock.MagicMock()
    with mock.patch('src.movecheck.iter_suspicious_moves', n):
        client.get('/movecheck?limit=0')
    n.assert_called_with(20)


def test_movecheck_limits_max(client):
    n = mock.MagicMock()
    with mock.patch('src.movecheck.iter_suspicious_moves', n):
        client.get('/movecheck?limit=max')
    n.assert_called_with(250)


def test_movecheck_limits_over(client):
    n = mock.MagicMock()
    with mock.patch('src.movecheck.iter_suspicious_moves', n):
        client.get('/movecheck?limit=500')
    n.assert_called_with(250)


def test_movecheck_limits_nonsense(client):
    n = mock.MagicMock()
    with mock.patch('src.movecheck.iter_suspicious_moves', n):
        client.get('/movecheck?limit=nonsense')
    n.assert_called_with(20)

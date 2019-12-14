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

import flask
import unittest.mock as mock
import sys
import os
sys.path.append(os.path.realpath(os.path.dirname(__file__)+"/.."))


def test_app():
    m = mock.Mock()
    n = mock.Mock()
    m.return_value = {'secret_key': 'Test'}
    with mock.patch('json.load', m):
        with mock.patch('builtins.open', n):
            from src.app import app
    assert type(app) is flask.app.Flask

    with app.test_client() as client:
        r = client.get('/')
        assert r.status_code == 200
        assert r.data is not None

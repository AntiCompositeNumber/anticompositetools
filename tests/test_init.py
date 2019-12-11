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
import json
import sys
import os
sys.path.append(os.path.realpath(os.path.dirname(__file__)+"/.."))
import src as anticompositetools  # noqa: E402


def test_create_app():
    __dir__ = os.path.realpath(os.path.dirname(__file__)+"/..")
    conf = os.path.join(__dir__, 'src/config.json')
    try:
        open(conf, 'r')
    except FileNotFoundError:
        with open(conf, 'w') as f:
            json.dump({'secret_key': 'Test'}, f)

    app = anticompositetools.create_app()
    assert type(app) is flask.app.Flask
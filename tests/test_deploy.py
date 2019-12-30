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

# import pytest
# import requests
# import mwparserfromhell as mwph
import unittest.mock as mock
import sys
import os

sys.path.append(os.path.realpath(os.path.dirname(__file__) + "/.."))
import src.deploy as deploy  # noqa: E402


def test_check_status():
    payload = {"deployment_status": {"state": "pending"}}
    assert deploy.check_status(payload)


def test_restart_webservice():
    m = mock.MagicMock()
    with mock.patch("subprocess.Popen", m):
        d = deploy.restart_webservice()
    assert d is None
    m.assert_called_once_with(["webservice", "restart"])

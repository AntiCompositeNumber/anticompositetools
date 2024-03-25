#!/usr/bin/env python3
# coding: utf-8
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright 2019 AntiCompositeNumber

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

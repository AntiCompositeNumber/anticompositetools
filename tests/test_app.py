#!/usr/bin/env python3
# coding: utf-8
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright 2019 AntiCompositeNumber

import flask
import unittest.mock as mock
import sys
import os
import pytest

sys.path.append(os.path.realpath(os.path.dirname(__file__) + "/.."))


@pytest.mark.skip(reason="Flaky test on GitHub actions apparently.")
def test_app():
    m = mock.Mock()
    n = mock.Mock()
    m.return_value = {"secret_key": "Test"}
    with mock.patch("json.load", m):
        with mock.patch("builtins.open", n):
            from src.app import app
    assert type(app) is flask.app.Flask

    with app.test_client() as client:
        r = client.get("/")
        assert r.status_code == 200
        assert r.data is not None

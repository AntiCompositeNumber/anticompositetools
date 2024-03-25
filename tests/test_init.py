#!/usr/bin/env python3
# coding: utf-8
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright 2019 AntiCompositeNumber

import flask
import sys
import os

sys.path.append(os.path.realpath(os.path.dirname(__file__) + "/.."))
import src  # noqa: E402


def client():
    conf = {"secret_key": "TestTest", "TESTING": True}
    app = src.create_app(test_config=conf)

    assert type(app) is flask.app.Flask

    with app.test_client() as client:
        r = client.get("/")
        assert r.status_code == 200
        assert r.data is not None

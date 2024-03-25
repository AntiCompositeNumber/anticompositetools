#!/usr/bin/env python3
# coding: utf-8
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright 2019 AntiCompositeNumber

import base64
import json
import logging
import os
import subprocess

import flask

logging.basicConfig(
    filename="act.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
)


def create_app(test_config=None):
    app = flask.Flask(__name__)

    __dir__ = os.path.dirname(__file__)
    try:
        conf = json.load(open(os.path.join(__dir__, "config.json")))
    except OSError:
        if test_config:
            app.config.update(test_config)
        else:
            raise
    else:
        app.config.update(conf)

    app.secret_key = base64.b64decode(app.config.pop("secret_key"))

    rev = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    app.config["version"] = rev.stdout

    from . import (
        hyphenator,
        citeinspector,
        deploy,
        paracheck,
        projectnew,
        filearchive,
        nearfar,
        dsalerts,
        newautopat,
    )

    app.register_blueprint(hyphenator.bp)
    app.register_blueprint(citeinspector.bp)
    app.register_blueprint(deploy.bp)
    app.register_blueprint(paracheck.bp)
    app.register_blueprint(projectnew.bp)
    app.register_blueprint(filearchive.bp)
    app.register_blueprint(nearfar.bp)
    app.register_blueprint(dsalerts.bp)
    app.register_blueprint(newautopat.bp)

    @app.route("/")
    def index():
        return flask.render_template("index.html")

    return app

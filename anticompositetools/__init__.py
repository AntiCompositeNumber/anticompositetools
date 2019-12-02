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

import logging
import os
import json
import base64
import subprocess
import flask

logging.basicConfig(filename='act.log', level=logging.DEBUG)


def create_app():
    app = flask.Flask(__name__)

    __dir__ = os.path.dirname(__file__)
    app.config.update(json.load(open(os.path.join(__dir__, 'config.json'))))
    app.secret_key = base64.b64decode(app.config['secret_key'])
    app.config['secret_key'] = None
    
    rev = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                         universal_newlines=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    app.config['version'] = rev.stdout

    from . import hyphenator
    app.register_blueprint(hyphenator.bp)

    @app.route('/')
    def index():
        return flask.render_template('index.html')

    return app

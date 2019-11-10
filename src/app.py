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
import hyphenator

app = flask.Flask(__name__)


@app.route('/')
def index():
    return flask.render_template('index.html')


@app.route('/hyphenator', methods=['GET'])
def hyphenator_form():
    return flask.render_template('hyphenator-form.html')


@app.route('/hyphenator/output', methods=['POST'])
def hyphenator_output():
    if flask.request.method == 'POST':
        pageurl = flask.request.form['page_url']

        if '?' in pageurl:
            submit_url = pageurl + '&action=submit'
        else:
            submit_url = pageurl + '?action=submit'
            newtext, times, count = hyphenator.main(pageurl)

        return flask.render_template(
                'hyphenator-output.html', count=count, submit_url=submit_url,
                newtext=newtext, edit_time=times[0], start_time=times[1])

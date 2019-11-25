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
import datetime
import subprocess
import flask
import hyphenator
import deploy

logging.basicConfig(filename='act.log', level=logging.DEBUG)

app = flask.Flask(__name__)

__dir__ = os.path.dirname(__file__)
app.config.update(json.load(open(os.path.join(__dir__, 'config.json'))))

rev = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                     universal_newlines=True, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
app.config['version'] = rev.stdout

def format_timesince(value):
    if value:
        date = datetime.strptime(value, 'YYYY-MM-DDTHH:MM:SS.mmmmmm')



@app.route('/')
def index():
    return flask.render_template('index.html')


@app.route('/linksearch')
def linksearch():
    with open('linkspam_config.json') as f:
        data = json.load(f)

    return flask.render_template('linkspam.html', data=data)


@app.route('/linksearch/job/<state>')
def linksearch_job(state):
    percent = flask.request.args.get('percent', '')
    return flask.render_template('linkspam_submit.html', state=state,
                                 percent=percent)


@app.route('/linksearch/result')
def linksearch_result():
    with open('output.json') as f:
        data = json.load(f)

    return flask.render_template('linkspam_result.html', data=data)


@app.route('/deploy', methods=['POST'])
def autodeploy():
    request = flask.request
    logging.debug('Request:' + str(request.__dict__))
    logging.debug('Request JSON:' + str(request.json))
    if deploy.verify_hmac(flask.request, app.config):
        try:
            deploy_result = deploy.deploy(request, request.json, app.config)
        except Exception as problem:
            logging.error(problem)
            return 'Exception while deploying:\n' + str(problem), 500
        if deploy_result:
            flask.abort(204)
        else:
            flask.abort(504)
    else:
        flask.abort(403)


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

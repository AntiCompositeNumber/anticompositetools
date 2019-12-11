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
import subprocess
import requests
import hmac
import flask

bp = flask.Blueprint('deploy', __name__, url_prefix='/deploy')


def pull_master():
    logging.info('Pulling from git repository')
    try:
        pull = subprocess.run(
            ['git', '-C', '~/anticompositetools/', 'pull'], check=True,
            universal_newlines=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        logging.debug(pull.stdout)
        logging.error(pull.stderr)
    except subprocess.CalledProcessError as cpe:
        logging.error(cpe)
        return False
    else:
        return True


def restart_webservice():
    logging.info('Webservice restarting!')
    subprocess.Popen(['webservice', 'restart'])


def update_status(url, status, auth):
    payload = {'state': status}
    headers = {'Accept': 'application/vnd.github.flash-preview+json'}
    response = requests.post(url, auth=auth, data=payload, headers=headers)
    logging.debug(response.text)
    return response.status_code == 201


def deploy(request, payload):
    logging.info('Deployment starting')
    logging.debug(payload)
    auth = ('AntiCompositeNumber',
            flask.current_app.config['github_deploy_pat'])
    status_url = payload['deployment']['statuses_url']
    if pull_master():
        update_status(status_url, 'in_progress', auth)
        restart_webservice()
        return True
    else:
        update_status(status_url, 'error', auth)
        return False


def check_status(payload):
    return payload.get('deployment_status', {}).get('state') == 'pending'


def verify_hmac(request):
    config = flask.current_app.config
    r_hmac = hmac.new((config['github_secret']).encode(),
                      msg=request.get_data(), digestmod='sha1')
    r_digest = 'sha1=' + r_hmac.hexdigest()
    g_digest = request.headers['X-Hub-Signature']
    return hmac.compare_digest(r_digest, g_digest)


@bp.route('/', methods=['POST'])
def autodeploy():
    request = flask.request
    logging.debug('Request:' + str(request.__dict__))
    logging.debug('Request JSON:' + str(request.json))
    if check_status(request.json) and verify_hmac(request):
        try:
            deploy_result = deploy(request, request.json)
        except Exception as problem:
            logging.error(problem)
            return 'Exception while deploying:\n' + str(problem), 500
        if deploy_result:
            flask.abort(204)
        else:
            flask.abort(504)
    else:
        flask.abort(403)

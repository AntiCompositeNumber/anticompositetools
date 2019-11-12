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

logging.basicConfig(filename='act.log', level=logging.DEBUG)


def verify_hmac(request, config):
    r_hmac = hmac.new((config['github_secret']).encode(),
                      msg=request.get_data(), digestmod='sha1')
    r_digest = 'sha1=' + r_hmac.hexdigest()
    g_digest = request.headers['X-Hub-Signature']
    return hmac.compare_digest(r_digest, g_digest)


def deploy(request, config):
    push_json = request.get_josn()
    push_ref = push_json['ref']
    if push_ref == 'refs/heads/master':
        logging.info('Push event recieved from GitHub for ' + push_ref)
        logging.debug(push_json['after'])

        deployment_payload = {'ref': push_ref}
        deployment_r = requests.post(
            push_json['deployments_url'], auth=config['github_deploy_pat'],
            payload=deployment_payload)
        if deployment_r.status_code == 201:
            deployment_json = deployment_r.json()
            deployment_url = deployment_json['url']
            logging.info('Pulling from git repository')
            try:
                pull = subprocess.run(
                    ['git', '-C', '~/anticompositetools/', 'pull'], check=True,
                    universal_newlines=True, capture_output=True)
                logging.debug(pull.stdout)
                logging.error(pull.stderr)
            except subprocess.CalledProcessError as cpe:
                logging.error(str(cpe))
                new_status = requests.post(deployment_url + '/statuses',
                                           payload={'state': 'failure'},
                                           auth=config['github_deploy_pat'])
                logging.debug(new_status.text)
                if new_status.status_code == 201:
                    return True
                else:
                    return False
            else:
                new_status = requests.post(deployment_url + '/statuses',
                                           payload={'state': 'success'},
                                           auth=config['github_deploy_pat'])
                logging.debug(new_status.text)
                if new_status.status_code == 201:
                    logging.info('Webservice restarting!')
                    subprocess.Popen(['webservice', 'restart'])
                    return True
                else:
                    return False

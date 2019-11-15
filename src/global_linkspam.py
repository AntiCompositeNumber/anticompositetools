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

"""Generates reports for a link cleanup project"""

import time
from datetime import datetime
import urllib.parse
import json
import argparse
import requests
import pywikibot
from pywikibot import pagegenerators

version = '1.2.2'


def get_sitematrix():
    """Request the sitematrix from the API, check if open, then yeild URLs"""

    def check_status(checksite):
        """Return true only if wiki is public and open"""
        return ((checksite.get('closed') is None)
                and (checksite.get('private') is None)
                and (checksite.get('fishbowl') is None))

    # Construct the request to the Extension:Sitematrix api
    payload = {"action": "sitematrix", "format": "json",
               "smlangprop": "site", "smsiteprop": "url"}
    headers = {'user-agent': 'HijackSpam ' + version + ' as AntiCompositeBot'
               + ' on Toolforge. User:AntiCompositeNumber, pywikibot/'
               + pywikibot.__version__}
    url = 'https://meta.wikimedia.org/w/api.php'

    # Send the request, except on HTTP errors, and try to decode the json
    r = requests.get(url, headers=headers, params=payload)
    r.raise_for_status()
    result = r.json()['sitematrix']

    # Parse the result into a generator of urls of public open wikis
    for key, lang in result.items():
        if key == 'count':
            continue
        elif key == 'specials':
            for site in lang:
                if check_status(site):
                    yield site['url']
        else:
            for site in lang['site']:
                if check_status(site):
                    yield site['url']


def list_pages(site, target):
    """Takes a site object and yields the pages linking to the target"""

    # Linksearch is specific, and treats http/https and TLD/subdomain
    # links differently, so we need to run through them all
    for num in range(0, 4):
        if num % 2 == 0:
            protocol = 'http'
        else:
            protocol = 'https'

        if num > 1:
            ctar = '*.' + target
        else:
            ctar = target

        for page in pagegenerators.LinksearchPageGenerator(
                ctar, site=site, protocol=protocol):
            yield page


def site_report(pages, site, preload_sums, report_site):
    """Generate the full linksearch report for a site"""

    summary = urllib.parse.quote(preload_sums.get(
        site.code, preload_sums.get('en')))
    reports = []

    for page in pages:
        url = page.full_url()
        edit_link = url + '?action=edit&summary=' + summary + '&minor=1'

        page_line = dict(page_title=page.title(),
                         page_link=url, edit_link=edit_link)

        if page_line not in reports:
            reports.append(page_line)

    count = len(reports)

    if count > 0:
        return {'reports': reports, 'count': count}
    else:
        return {}


def summary_table(counts):
    """Takes a dictionary of dbnames and counts and returns at table"""

    entries = {key: value for key, value in counts.items() if value != 0}
    total_pages = sum(entries.values())
    total_wikis = len(entries)

    return dict(entries=entries, total_pages=total_pages,
                total_wikis=total_wikis)


def run_check(site, runOverride):
    runpage = pywikibot.Page(site, 'User:AntiCompositeBot/HijackSpam/Run')
    run = runpage.text.endswith('True')
    if run is False and runOverride is False:
        print('Runpage is false, quitting...')
        raise pywikibot.UserBlocked


def save_page(new_text, target):
    with open(target + '.json',
              'w') as f:
        json.dump(new_text, f, indent=4)


def main():
    counts = {}
    output = {}

    parser = argparse.ArgumentParser(description='Generate global link usage')
    parser.add_argument(
        'target', help='Domain, such as "example.com", to search for')
    target = parser.parse_args().target

    # Set up on enwiki, check runpage, and prepare empty report page
    enwiki = pywikibot.Site('en', 'wikipedia')
    run_check(enwiki, False)

    # Load preload summaries from on-wiki json
    config = pywikibot.Page(
        enwiki, 'User:AntiCompositeBot/HijackSpam/config.json')
    preload_sums = json.loads(config.text)

    # Get the list of sites from get_sitematrix(), retrying once
    try:
        sitematrix = get_sitematrix()
    except requests.exceptions:
        time.sleep(5)
        sitematrix = get_sitematrix()

    # Add the start time and target to the output
    output['target'] = target
    output['start_time'] = datetime.utcnow().isoformat()

    # Run through the sitematrix. If pywikibot works on that site, generate
    # a report. Otherwise, add it to the skipped list.
    skipped = []
    site_reports = {}
    letter = ''
    for url in sitematrix:
        if letter != url[8]:
            letter = url[8]
            print('\r' + letter)

        try:
            cur_site = pywikibot.Site(url=url + '/wiki/MediaWiki:Delete/en')
        except Exception:
            skipped.append(url)
            continue
        pages = list_pages(cur_site, target)

        report = site_report(pages, cur_site, preload_sums, enwiki)

        if report:
            site_reports[cur_site.dbName()] = report
            counts[cur_site.dbName()] = report['count']

    output['site_reports'] = site_reports
    output['skipped'] = skipped
    # Generate a summary table and stick it at the top
    output['summary_table'] = summary_table(counts)
    # Save the report
    save_page(output)


if __name__ == '__main__':
    main()

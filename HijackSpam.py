#!/usr/bin/env python
# coding: utf-8

# # HijackSpam
# Looking for the use of a domain anywhere.
# 
# [Per-wiki results](#Results) - [Summary table](#Summary)

# In[6]:


import time
import urllib.parse
import requests
from IPython import display
import pywikibot
from pywikibot import pagegenerators

def get_sitematrix():
    """Request the sitematrix from the API, check if open, then yeild URLs"""
    
    def check_status(checksite):
        """Return true only if wiki is public and open"""
        return ((checksite.get('closed') is None)
            and (checksite.get('private') is None)
            and (checksite.get('fishbowl') is None))
    
    
    payload = {"action": "sitematrix", "format": "json",
               "smlangprop": "site", "smsiteprop": "url",}
    headers = {'user-agent':
               'HijackSpam on PAWS; User:AntiCompositeBot, pywikibot/'
               + pywikibot.__version__}
    url = 'https://meta.wikimedia.org/w/api.php'
    r = requests.get(url, headers=headers, params=payload)
    r.raise_for_status()
    
    result = r.json()['sitematrix']
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
    """Takes a pywikibot site object and yeilds the pages linking to the target"""
    
    for num in range(0,4):
        if num % 2 == 0:
            protocol = 'http'
        else:
            protocol = 'https'
            
        if num > 1:
            ctar = '*.' + target
        else:
            ctar = target
        
        for page in pywikibot.pagegenerators.LinksearchPageGenerator(
            ctar, site=site, protocol=protocol):
            yield page

            
def output(text):
    display.display_markdown(text, raw=True)
    
    
def prep_markdown(pages, site, preload_sums):
    summary = urllib.parse.quote(preload_sums.get(site.code, preload_sums.get('en')))
    md = '' 
    count = 0
    for page in pages:
        count += 1
        md += f'* [{page.title()}]({page.full_url()}) ([edit]({page.full_url()}?action=edit&summary={summary}&minor=1))\n'
    if count > 0:
        md = f'## {site.dbName()}: {count} \n' + md
        output(md)
        return count

    
def summary_table(counts):
    tot = 0
    md = '## Summary\n\n|Wiki|Count|\n|---|---|\n'
    wt = '{| class="wikitable"\n|-\n! Wiki !! Count !! Volunteer !! Progress\n'
    for wiki, count in counts.items():
        if count is not None:
            md += f'|{wiki}|{str(count)}|\n'
            wt += f'|-\n| {wiki} || {str(count)} || || \n'
            tot += count
    
    wt += '|}'
    md += '\nTotal: ' + str(tot) + '\n```\n' + wt + '\n```\n'
    output(md)
    
        
def main():
    target = 'blackwell-synergy.com'
    preload_sums = {
        'en': 'Replacing links to hijacked website, see [[:m:Steward_requests/Miscellaneous#Hijacked_domain_and_predatory_spam|here]]',
        'fr': "Remplacement des liens à une site détourné ([[:m:Steward_requests/Miscellaneous#Hijacked_domain_and_predatory_spam|Plus d'information]])",
        'pt': 'corrigindo DOI de site "sequestrado", ver [[:m:Steward_requests/Miscellaneous#Hijacked_domain_and_predatory_spam|aqui]]'
    }
    
    counts = {}
    try:
        sitematrix = get_sitematrix()
    except requests.exceptions:
        time.sleep(5)
        sitematrix = get_sitematrix()
        
    output('Scanning all public wikis for ' + target + ' at ' + time.asctime() + '\n')
    for url in sitematrix:
        try:
            cur_site = pywikibot.Site(url=url + '/wiki/MediaWiki:Delete/en')
        except Exception:
            output('Skipping ' + url)
            continue
            
        pages = list_pages(cur_site, target)
        counts[cur_site.dbName()] = prep_markdown(pages, cur_site, preload_sums)
        
    summary_table(counts)
    output('Finished')


# # Results

# In[7]:


main()


# ### Licensing
# Copyright 2019 AntiCompositeNumber
# 
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
# 
# ### To fork:
# 1. Open the [raw page](?format=raw) and save it to your computer
# 2. Go to your [PAWS control panel](https://paws.wmflabs.org/paws/hub) and sign in using OAUTH
# 3. Click Upload and upload the file from step 1
# 4. To run, open the notebook and click Cell > Run All

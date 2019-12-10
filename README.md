# AntiCompositeTools
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/AntiCompositeNumber/anticompositetools/Python%20application) ![Uptime Robot status](https://img.shields.io/uptimerobot/status/m783972628-037856cb670609254a10c883?label=website%20status)

A group of tools built for the English Wikipedia and other Wikimedia projects, written in Python using Flask and running on Wikimedia Toolforge.

## Hyphenator
https://tools.wmflabs.org/anticompositetools/hyphenator
Normlises the format of ISBNs using [python-stdnum](https://arthurdejong.org/python-stdnum/).

Uses:
* [requests](https://2.python-requests.org/en/master/)
* [mwparserfromhell](https://github.com/earwig/mwparserfromhell)
* [stdnum](https://github.com/arthurdejong/python-stdnum)

## CiteInspector
https://tools.wmflabs.org/anticompositetools/citeinspector
Compares existing citations in an article to data from Citoid.

Uses:
* [requests](https://2.python-requests.org/en/master/)
* [mwparserfromhell](https://github.com/earwig/mwparserfromhell)
* [fuzzywuzzy](https://github.com/seatgeek/fuzzywuzzy) 

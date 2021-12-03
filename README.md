# AntiCompositeTools
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/AntiCompositeNumber/anticompositetools/Python%20application)
![Uptime Robot status](https://img.shields.io/uptimerobot/status/m783972628-037856cb670609254a10c883?label=website%20status)
[![Coverage Status](https://coveralls.io/repos/github/AntiCompositeNumber/anticompositetools/badge.svg?branch=master)](https://coveralls.io/github/AntiCompositeNumber/anticompositetools?branch=master)
![Python version 3.9](https://img.shields.io/badge/python-v3.9-blue)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A group of tools built for the English Wikipedia and other Wikimedia projects, written in Python using Flask and running on Wikimedia Toolforge.

## Hyphenator
https://anticompositetools.toolforge.org/hyphenator
Normlises the format of ISBNs using [python-stdnum](https://arthurdejong.org/python-stdnum/).

Uses:
* [requests](https://2.python-requests.org/en/master/)
* [mwparserfromhell](https://github.com/earwig/mwparserfromhell)
* [stdnum](https://github.com/arthurdejong/python-stdnum)

## CiteInspector
https://anticompositetools.toolforge.org/citeinspector
Compares existing citations in an article to data from Citoid.

Uses:
* [requests](https://2.python-requests.org/en/master/)
* [mwparserfromhell](https://github.com/earwig/mwparserfromhell)
* [fuzzywuzzy](https://github.com/seatgeek/fuzzywuzzy)

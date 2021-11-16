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
import pywikibot  # type: ignore
import mwparserfromhell as mwph  # type: ignore
from typing import Tuple, List, Dict

bp = flask.Blueprint("paracheck", __name__, url_prefix="/paracheck")


def main() -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    site = pywikibot.Site("en", "wikipedia")
    template = pywikibot.Page(site, "Template:ConfirmationOTRS")
    known_licenses = {
        "pd",
        "cc0",
        "Public domain",
        "public domain",
        "attribution",
        "cc-by-3.0",
        "cc-by-4.0",
        "cc",
        "cc3",
        "cc-by-sa",
        "cc-by-sa-3.0",
        "gfdl",
        "dual",
        "d",
        "both",
        "g",
    }
    known_usage: Dict[str, List[str]] = {}
    unknown_usage: Dict[str, List[str]] = {}

    for page in site.page_embeddedin(template):
        code = mwph.parse(page.text)
        for transclusion in code.ifilter_templates(matches="ConfirmationOTRS"):
            if transclusion.has("license", ignore_empty=True):
                license = str(transclusion.get("license").value).strip().lower()
            elif transclusion.has("licence", ignore_empty=True):
                license = str(transclusion.get("licence").value).strip().lower()
            else:
                license = ""

            if license in known_licenses:
                known_usage.setdefault(license, []).append(page.full_url())
            else:
                unknown_usage.setdefault(license, []).append(page.full_url())

    return known_usage, unknown_usage


@bp.route("")
def paracheck():
    known_usage, unknown_usage = main()

    known_counts = {license: len(urls) for license, urls in known_usage.items()}
    unknown_counts = {license: len(urls) for license, urls in unknown_usage.items()}
    unknown_total = sum(unknown_counts.values())

    return flask.render_template(
        "paracheck.html",
        unknown_usage=unknown_usage,
        known_counts=known_counts,
        unknown_counts=unknown_counts,
        unknown_total=unknown_total,
    )

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
import mwparserfromhell as mwph
import pywikibot
import requests

bp = flask.Blueprint("movecheck", __name__, url_prefix="/movecheck")


def get_AFC_reviewers(site):
    page = pywikibot.Page(
        site, "Wikipedia:WikiProject Articles for creation/Participants"
    )
    code = mwph.parse(page.text)
    return {
        str(template.get(1)) for template in code.ifilter_templates(matches="user2")
    }


def gen_recent_moves(site):
    for event in site.logevents(logtype="move"):  # pragma: no branch
        if (
            event.target_ns == 0
            and event.ns() != 0
            and "Draft:Move" not in event.page().title()
        ):
            yield event


def check_deletions(page, site):
    """If the page has previously been deleted, return True"""
    for event in site.logevents(logtype="delete", page=page):
        if event.action() == "restore":
            continue
        elif any(i in event.comment() for i in {"G13", "G7", "R2"}):
            continue
        else:
            return True
    else:
        return False


def check_now_deleted(page):
    """Returns true if the page is deleted"""
    # simple check for any content, does catch blanked pages though
    return not page.text


def check_declines(page):
    """Returns true if the page has been previously declined"""
    for rev in page.revisions():
        if (
            "Declining submission" in rev.comment
            or "Rejecting submission" in rev.comment
        ):
            return True
    else:
        return False


def batch_pages(keys):
    for i in range(0, len(keys), 45):
        yield keys[i : i + 45]


def batch_ores(data):
    for batch in batch_pages(list(data)):
        revids = "|".append(batch)
        query_ores(revids)


def query_ores(revids):
    raise NotImplementedError
    payload = {"models": "draftquality", "revids": revids}
    url = "https://ores.wikimedia.org/v3/scores/enwiki/"

    response = requests.get(url, params=payload)
    response.raise_for_status()
    json = response.json()

    data = json["scores"]
    data


def log_metadata(site, event):
    page = event.target_page
    old_page = event.page()
    username = event.user()
    user = pywikibot.page.User(site, username)
    return {
        "title": page.title(),
        "old_title": old_page.title(),
        "url": page.full_url(),
        "old_url": old_page.full_url(),
        "timestamp": str(event.timestamp()),
        "user": username,
        "user_url": user.getUserPage().full_url(),
        "user_talk_url": user.getUserTalkPage().full_url(),
        "user_contribs_url": (
            "https://en.wikipedia.org/wiki/Special:Contribs/" + username
        ),
        "comment": event.comment(),
    }


def iter_suspicious_moves(limit):
    site = pywikibot.Site("en", "wikipedia")
    reviewers = get_AFC_reviewers(site)

    i = 0
    for move in gen_recent_moves(site):  # pragma: no branch
        if i == limit:
            break
        old_page = move.page()
        new_page = move.target_page
        tags = ["non-AfC-move"]
        if move.user() in reviewers or check_now_deleted(new_page):
            continue
        if check_deletions(old_page, site):
            tags.append("previous-ns0-del")
        if check_deletions(new_page, site):
            tags.append("previous-draft-del")
        if check_declines(new_page):
            tags.append("previous-afc-decline")

        data = log_metadata(site, move)
        data["tags"] = tags
        i += 1
        yield data


@bp.route("")
def movecheck():
    raw_limit = flask.request.args.get("limit", default="20")
    try:
        int_limit = int(raw_limit)
    except ValueError:
        if raw_limit == "max":
            limit = 250
        else:
            limit = 20
    else:
        if int_limit < 1:
            limit = 20
        elif int_limit > 250:
            limit = 250
        else:
            limit = int_limit

    moves = iter_suspicious_moves(limit)
    return flask.render_template("movecheck.html", data=moves)

#!/usr/bin/env python3
# coding: utf-8
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright 2020 AntiCompositeNumber

import toolforge
import flask
from typing import Iterator, Dict

bp = flask.Blueprint("newautopat", __name__, url_prefix="/newautopat")
base_url = "https://en.wikipedia.org/wiki"


def run_query(limit=100, hideredirs=False) -> Iterator[Dict[str, str]]:
    where = ""
    if hideredirs:
        where += "AND page_is_redirect = 0"
    query = f"""
SELECT rc_timestamp, rc_title, actor_name, comment_text
FROM recentchanges
JOIN actor_revision ON rc_actor = actor_id
JOIN user_groups ON actor_user = ug_user
JOIN comment_recentchanges ON rc_comment_id = comment_id
JOIN page ON rc_cur_id = page_id
WHERE
    rc_namespace = 0
    AND ug_group = "autoreviewer"
    AND rc_new = 1
    {where}
ORDER BY rc_timestamp DESC
LIMIT {limit}
"""
    conn = toolforge.connect("enwiki_p")
    with conn.cursor() as cur:
        cur.execute(query)
        data = cur.fetchall()

    for row in data:
        line = {
            "timestamp": str(row[0], encoding="utf-8"),
            "title": str(row[1], encoding="utf-8"),
            "user": str(row[2], encoding="utf-8").replace(" ", "_"),
            "comment": str(row[3], encoding="utf-8"),
        }
        line["user_url"] = f"{base_url}/User:{line['user']}"
        line["user_talk_url"] = f"{base_url}/User_talk:{line['user']}"
        line["user_contribs_url"] = f"{base_url}/Special:Contribs/{line['user']}"
        line["url"] = f"{base_url}/{line['title']}"
        yield line


@bp.route("/")
def results():
    limit = int(flask.request.args.get("limit", 100))
    hideredirs = bool(flask.request.args.get("hideredirs", False))
    data = run_query(limit=limit, hideredirs=hideredirs)
    return flask.render_template(
        "newautopat_results.html", data=data, limit=limit, hideredirs=hideredirs
    )

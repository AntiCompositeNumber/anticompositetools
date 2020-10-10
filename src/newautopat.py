#!/usr/bin/env python3
# coding: utf-8
# SPDX-License-Identifier: Apache-2.0


# Copyright 2020 AntiCompositeNumber

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import toolforge
import flask
from typing import Iterator, Dict

bp = flask.Blueprint("newautopat", __name__, url_prefix="/newautopat")
base_url = "https://en.wikipedia.org/wiki"


def run_query(limit=100) -> Iterator[Dict[str, str]]:
    query = """
SELECT rc_timestamp, rc_title, actor_name, comment_text
FROM recentchanges
JOIN actor_revision ON rc_actor = actor_id
JOIN user_groups ON actor_user = ug_user
JOIN comment_recentchanges ON rc_comment_id = comment_id
WHERE
    rc_namespace = 0
    AND ug_group = "autoreviewer"
    AND rc_new = 1
ORDER BY rc_timestamp DESC
LIMIT %s
"""
    conn = toolforge.connect("enwiki_p")
    with conn.cursor() as cur:
        cur.execute(query, args=(limit))
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
    limit = flask.request.args.get("limit", 100)
    data = run_query(limit)
    return flask.render_template("newautopat_results.html", data=data)

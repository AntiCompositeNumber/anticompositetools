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
import pymysql.cursors
import phpserialize

bp = flask.Blueprint("filearchive", __name__, url_prefix="/filearchive")

try:
    f = open("/etc/wmcs-project")
except FileNotFoundError:
    wmcs = False
else:
    f.close()
    wmcs = True


def query_database(dbname="commonswiki", page=""):
    assert page
    if not wmcs:
        raise OSError
    # TODO: select only needed rows instead of ignoring later
    query = """
SELECT
  (
    SELECT
      actor_name
    FROM
      actor
    WHERE
      actor_id = fa_actor
  ) as upload_user,
  (
    SELECT
      user_name
    FROM
      `user`
    WHERE
      user_id = fa_deleted_user
  ) as deleted_user,
  filearchive.*,
  (
    SELECT
      comment_text
    FROM
      `comment`
    WHERE
      comment_id = fa_description_id
  ) as upload_comment,
  (
    SELECT
      comment_text
    FROM
      `comment`
    WHERE
      comment_id = fa_deleted_reason_id
  ) as deleted_comment
FROM
  filearchive
WHERE
  fa_name = %s
"""
    conn = toolforge.connect(dbname)
    with conn.cursor(cursor=pymysql.cursors.DictCursor) as cur:
        cur.execute(query, (page))
        return cur.fetchall()


def process_db_result(raw_data):
    data = {}
    # remove non-useful keys to other dbs
    for key in {
        "fa_id",
        "fa_deleted_user",
        "fa_deleted_reason_id",
        "fa_description_id",
        "fa_actor",
    }:
        raw_data.pop(key, None)

    # handle metadata PHP array
    data["fa_metadata"] = phpserialize.loads(
        raw_data.pop("fa_metadata", ""), decode_strings=True
    )

    # stringify everything else
    for key, value in raw_data.items():
        if not value:
            continue
        elif isinstance(value, bytes):
            # decode unicode strings
            data[key] = str(value, encoding="utf-8")
        else:
            data[key] = str(value)

    return data


@bp.route("/")
def form():
    dbname = flask.request.args.get("dbname")
    page = flask.request.args.get("filename")
    if dbname and page:
        return flask.redirect(flask.url_for("filearchive.main", wiki=dbname, page=page))
    else:
        return flask.render_template(
            "filearchive-form.html", sitematrix=["enwiki", "arwiki", "commonswiki"]
        )


@bp.route("/<wiki>/<page>")
def main(wiki, page):
    if page.startswith("File:"):
        page = page.rpartition("File:")[2]

    if ":" in "page":
        raise ValueError

    raw_data = query_database(wiki, page)
    data = [process_db_result(line) for line in raw_data]
    return str(data)

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

bp = flask.Blueprint("filearchive", __name__, url_prefix="/filearchive")


def query_database(dbname="commonswiki", page=""):
    assert page
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

    data = query_database(wiki, page)
    print(data)
    return str(data)

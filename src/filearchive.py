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
from decimal import Decimal

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
        # test data
        return [
            {
                "upload_user": b"AntiCompositeNumber",
                "deleted_user": b"Arthur Crbz",
                "fa_id": 5962279,
                "fa_name": b"Blaze_Pizza's_Artisan_Pizza.jpg",
                "fa_archive_name": None,
                "fa_storage_group": b"deleted",
                "fa_storage_key": None,
                "fa_deleted_user": 3768717,
                "fa_deleted_timestamp": b"20200129082735",
                "fa_deleted_reason_id": 137788728,
                "fa_size": 2827521,
                "fa_width": 5184,
                "fa_height": 3456,
                "fa_metadata": (
                    b"a:36:{"
                    b's:4:"Make";s:5:"Canon";'
                    b's:5:"Model";s:13:"Canon EOS 60D";'
                    b's:11:"Orientation";i:1;'
                    b's:11:"XResolution";s:4:"72/1";'
                    b's:11:"YResolution";s:4:"72/1";'
                    b's:14:"ResolutionUnit";i:2;'
                    b's:8:"Software";s:12:"Photos 1.0.1";'
                    b's:8:"DateTime";s:19:"2015:05:01 12:02:28";'
                    b's:12:"ExposureTime";s:4:"1/80";'
                    b's:7:"FNumber";s:3:"4/1";'
                    b's:15:"ExposureProgram";i:2;'
                    b's:15:"ISOSpeedRatings";i:1000;'
                    b's:11:"ExifVersion";s:4:"0230";'
                    b's:16:"DateTimeOriginal";s:19:"2015:05:01 12:02:28";'
                    b's:17:"DateTimeDigitized";s:19:"2015:05:01 12:02:28";'
                    b's:23:"ComponentsConfiguration";a:5:{'
                    b'i:0;i:1;i:1;i:2;i:2;i:3;i:3;i:0;s:5:"_type";s:2:"ol";}'
                    b's:17:"ShutterSpeedValue";s:4:"51/8";'
                    b's:13:"ApertureValue";s:3:"4/1";'
                    b's:17:"ExposureBiasValue";s:3:"0/1";'
                    b's:16:"MaxApertureValue";s:3:"4/1";'
                    b's:12:"MeteringMode";i:5;'
                    b's:5:"Flash";i:16;'
                    b's:11:"FocalLength";s:4:"58/1";'
                    b's:10:"SubSecTime";s:2:"00";'
                    b's:18:"SubSecTimeOriginal";s:2:"00";'
                    b's:19:"SubSecTimeDigitized";s:2:"00";'
                    b's:15:"FlashPixVersion";s:4:"0100";'
                    b's:10:"ColorSpace";i:1;'
                    b's:21:"FocalPlaneXResolution";s:8:"97379/17";'
                    b's:21:"FocalPlaneYResolution";s:9:"331079/57";'
                    b's:24:"FocalPlaneResolutionUnit";i:2;'
                    b's:14:"CustomRendered";i:0;'
                    b's:12:"ExposureMode";i:0;'
                    b's:12:"WhiteBalance";i:0;'
                    b's:16:"SceneCaptureType";i:0;'
                    b's:22:"MEDIAWIKI_EXIF_VERSION";i:2;}'
                ),
                "fa_bits": 8,
                "fa_media_type": b"BITMAP",
                "fa_major_mime": b"image",
                "fa_minor_mime": b"jpeg",
                "fa_description_id": Decimal("76801283"),
                "fa_actor": 3465,
                "fa_timestamp": b"20170630153739",
                "fa_deleted": 0,
                "fa_sha1": b"cfn5g1q6ptjpdcbk2eptx2l686hsw35",
                "upload_comment": (
                    b"Transferred from "
                    b"[[w:File:Blaze Pizza's Artisan Pizza.jpg|en.wikipedia]] "
                    b"([[w:Wikipedia:MTC!|MTC!]]) (1.0.0)"
                ),
                "deleted_comment": (
                    b"Media missing permission as of 21 January 2020. "
                    b"Please send a [[COM:Consent|permission statement]] "
                    b"to undelete this file."
                ),
            }
        ]
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

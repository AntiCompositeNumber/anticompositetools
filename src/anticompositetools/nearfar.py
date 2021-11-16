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

import flask
import requests
import itertools
from werkzeug.datastructures import MultiDict

# import re

bp = flask.Blueprint("nearfar", __name__, url_prefix="/nearfar")
session = requests.Session()
session.headers.update(
    {
        "User-Agent": "anticompositetools/nearfar "
        "(https://anticompositetools.toolforge.org/nearfar; "
        "tools.anticompositetools@tools.wmflabs.org) python-requests/"
        + requests.__version__
    }
)


@bp.route("/")
def form():
    args = MultiDict(flask.request.args)
    coord = args.pop("site", None), args.pop("lat", None), args.pop("lon", None)
    if all(coord):
        return flask.redirect(
            flask.url_for(
                "nearfar.display", site=coord[0], lat=coord[1], lon=coord[2], **args
            )
        )

    return flask.render_template("nearfar_form.html")


@bp.route("/<site>/<lat>/<lon>")
def display(site, lat, lon):
    args = flask.request.args
    url = f"https://{site}/w/api.php"
    pipe_coord = f"{lat}|{lon}"
    limit = int(args.get("limit", 50))
    radius = int(args.get("radius", 10000))
    if radius > 10000 or radius == "max":
        radius = 10000
    if limit > 500 or limit == "max":
        limit = 500
    params = {
        "action": "query",
        "format": "json",
        "prop": "description|pageimages|info",
        "list": "geosearch",
        "generator": "geosearch",
        "formatversion": "2",
        "piprop": "thumbnail|name",
        "inprop": "url",
        "gscoord": pipe_coord,
        "gsradius": radius,
        "gslimit": limit,
        "ggscoord": pipe_coord,
        "ggsradius": radius,
        "ggslimit": limit,
        "pilicense": "free",
        "pithumbsize": 100,
    }
    res = session.get(url, params=params)
    res.raise_for_status()
    api_data = {}
    for item in itertools.chain(
        res.json()["query"]["pages"], res.json()["query"]["geosearch"]
    ):
        # if item.get("thumbnail", {}).get("source"):
        #     thumb = item["thumbnail"]["source"]
        #     item["thumbnail"]["source"] = re.sub(
        api_data.setdefault(item["pageid"], {}).update(item)

    data = list(api_data.values())
    data.sort(key=lambda i: i["dist"])
    return flask.render_template("nearfar_display.html", data=data, lat=lat, lon=lon)

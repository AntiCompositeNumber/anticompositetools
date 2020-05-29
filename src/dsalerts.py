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
import datetime
import requests
import re
import logging
import json
import seaborn
import itertools
import mwparserfromhell as mwph
from typing import Set, NamedTuple, Iterator, Dict, Union, List, cast, Sequence

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

bp = flask.Blueprint("dsalerts", __name__, url_prefix="/dsalerts")
session = requests.Session()
session.headers.update(
    {
        "User-Agent": "anticompositetools/dsalerts "
        "(https://anticompositetools.toolforge.org/dsalerts ; "
        "tools.anticompositetools@tools.wmflabs.org) python-requests/"
        + requests.__version__
    }
)
Topics = Dict[str, Dict[str, str]]
Cases = Dict[str, Dict[str, Union[str, List[str]]]]


class DsAlert(NamedTuple):
    timestamp: datetime.datetime
    alerted_user: str
    sending_user: str
    topic_code: str


def get_ds_alert_hits(
    start_date: datetime.datetime, end_date: datetime.datetime
) -> Iterator[DsAlert]:
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "abuselog",
        "format": "json",
        "formatversion": 2,
        "aflstart": start_date.isoformat(),
        "aflend": end_date.isoformat(),
        "afldir": "newer",
        "aflfilter": 602,
        "afllimit": "max",
        "aflprop": "user|title|result|timestamp|details|revid",
    }
    for i in range(10):
        res = session.get(url, params=params)
        res.raise_for_status()
        raw_data = res.json()
        for hit in raw_data["query"]["abuselog"]:
            if hit["result"] == "tag":
                for alert in parse_alert_data(hit):
                    yield alert

        if raw_data.get("continue"):
            logger.debug(f"Continue: {raw_data['continue']}")
            params.update(raw_data["continue"])
        else:
            break
    else:
        # flask.abort(400)
        pass


class DsTopics:
    _topics = None
    _cases = None
    _aliases = None
    last_update = None

    @classmethod
    def topics(cls) -> Topics:
        if not cls._topics or (
            datetime.datetime.now() - cls.last_update > datetime.timedelta(minutes=30)
        ):
            cls.get_data()
        return cast(Topics, cls._topics)

    @classmethod
    def cases(cls) -> Cases:
        if not cls._cases or (
            datetime.datetime.now() - cls.last_update > datetime.timedelta(minutes=30)
        ):
            cls.get_data()
        return cast(Cases, cls._cases)

    @classmethod
    def aliases(cls) -> Dict[str, str]:
        if not cls._aliases or (
            datetime.datetime.now() - cls.last_update > datetime.timedelta(minutes=30)
        ):
            cls.get_data()
        return cast(Dict[str, str], cls._aliases)

    @classmethod
    def get_data(cls):
        topics: Topics = {}
        for page in ["Template:Ds/topics", "Template:Gs/topics"]:
            url = f"https://en.wikipedia.org/w/index.php?title={page}&action=raw"
            res = session.get(url)
            res.raise_for_status()
            key = ""
            keys = {"sanctions scope": "scope", "sanctions link": "page"}
            for line in res.text.split("\n"):
                if "<!-- -->" in line:
                    break
                elif line.startswith("|"):
                    code, sep, val = line[1:].partition("=")
                    if not sep or code == "#default":
                        continue
                    else:
                        topics.setdefault(code, {})[key] = val
                elif "{{SAFESUBST" in line:
                    regex = r"lc:\{{3}(.*?)\|\}{5}"
                    match = re.search(regex, line)
                    if match:
                        key = keys.get(match.group(1), "")
                elif "{{{|safesubst:" in line:
                    regex = r"#switch:\{{3}(.*?)\|\}{3}"
                    match = re.search(regex, line)
                    if match:
                        key = keys.get(match.group(1), "")

        cases: Cases = {}
        for code, topic in topics.items():
            topic["case"] = topic["page"].rpartition("/")[2]
            case = cases.setdefault(topic["case"], {"page": topic["page"]})
            if topic.get("scope"):
                case.setdefault("scope", topic["scope"])
            cast(list, case.setdefault("codes", [])).append(code)

        aliases = {}
        for case, topic in cases.items():
            codes = topic["codes"]
            for code in codes:
                aliases[code] = codes[0]

        cls._topics = topics
        cls._cases = cases
        cls._aliases = aliases
        cls.last_update = datetime.datetime.now()


def normalize_topic(topic: str) -> str:
    return DsTopics.aliases().get(topic, topic)


def parse_alert_data(hit: dict) -> List[DsAlert]:
    regex = (
        r"\{\{\s*subst:(?:template:)?(?:ds[ /]alert|sblp|blpse|alert|arbcom-alert|"
        r"arbcom–alert|uw-sanctions|T:DSA|uw-alert|discretionary[ _]sanctions[ /]alert"
        r"|alerting|gs/alert|uw-probation).*\|.*\}\}"
    )
    alerts = []
    text = "\n".join(hit["details"]["added_lines"])
    wikicode = mwph.parse(text)
    for template in wikicode.ifilter_templates(matches=regex):
        for param in ["1", "t", "topic"]:
            if template.has(param):
                topic_code = normalize_topic(
                    str(template.get(param)).rpartition("=")[2]
                )
                break
        else:
            continue
        if not topic_code or topic_code == "topic code":
            continue
        alerts.append(
            DsAlert(
                timestamp=datetime.datetime.fromisoformat(hit["timestamp"][:-1]),
                alerted_user=hit["details"]["page_title"],
                sending_user=hit["user"],
                topic_code=topic_code,
            )
        )
    return alerts


def filter_alert(alert: DsAlert, filters: Dict[str, Set[str]]):
    for key, values in filters.items():
        if getattr(alert, key) not in values:
            return False
    else:
        return True


def timeseries_data(
    start_date: datetime.datetime,
    resolution: str,
    end_date: datetime.datetime = datetime.datetime.utcnow(),
    filters: Dict[str, Set[str]] = {},
):
    replace = {
        "second": {},
        "day": {},
        "month": {"day": 1},
        "year": {"day": 1, "month": 1},
    }
    alerts = [
        alert
        for alert in get_ds_alert_hits(start_date, end_date)
        if filter_alert(alert, filters)
    ]
    data = {}
    for alert in alerts:
        timestamp = alert.timestamp
        if resolution != "second":
            timestamp = timestamp.date()
        timestamp = timestamp.replace(**replace[resolution]).isoformat()
        data[timestamp][alert.topic_code] = (
            data.setdefault(timestamp, {}).get(alert.topic_code, 0) + 1
        )
    totals = {}
    for date, counts in data.items():
        date_total = 0
        for topic, count in counts.items():
            date_total += count
            totals[topic] = totals.get(topic, 0) + count
        counts["Total"] = date_total
    totals["Total"] = sum(totals.values())
    data["Total"] = totals
    return data


@bp.route("/api/topics/<datatype>")
def api_topics(datatype):
    data = getattr(DsTopics, datatype)
    return flask.jsonify(data())


def pipe_args(arglist: Sequence[str]) -> Iterator[str]:
    for argstr in arglist:
        for arg in argstr.split("|"):
            yield arg.strip()


def get_data(args):
    now = datetime.datetime.utcnow()
    if args.get("start_date"):
        start_date = datetime.datetime.fromisoformat(args["start_date"])
    else:
        start_date = now.replace(month=now.month - 1)
    if args.get("end_date"):
        end_date = datetime.datetime.fromisoformat(args["end_date"]).replace(
            hour=23, minute=59, second=59
        )

    filters = {}
    if args.get("topic", "all") != "all":
        filters["topic_code"] = set(
            normalize_topic(topic) for topic in pipe_args(args.getlist("topic"))
        )
    if args.get("sending_user"):
        filters["sending_user"] = set(pipe_args(args.getlist("sending_user")))
    if args.get("alerted_user"):
        filters["alerted_user"] = set(pipe_args(args.getlist("alerted_user")))

    data = timeseries_data(
        start_date=start_date,
        resolution=args["resolution"],
        end_date=end_date,
        filters=filters,
    )
    return data


@bp.route("/api/data")
def api_data():
    return flask.jsonify(get_data(flask.request.args))


def colors():
    palette = seaborn.color_palette("muted", len(DsTopics.cases()))
    for color in palette:
        color = tuple(v * 255 for v in color)
        yield f"rgb{str(color)}"


@bp.route("/data")
def show_data():
    data = get_data(flask.request.args)
    topics = set(itertools.chain(*(val.keys() for val in data.values())))
    logger.debug(topics)
    chart = [
        {
            "label": case,
            "data": [
                {"x": date, "y": counts.get(cdata["codes"][0], 0)}
                for date, counts in data.items()
                if date != "Total"
            ],
            "backgroundColor": color,
            "borderColor": color,
            "hoverBackgroundColor": color,
        }
        for (case, cdata), color in zip(DsTopics.cases().items(), colors())
        if cdata["codes"][0] in topics
    ]
    return flask.render_template(
        "dsalerts_data.html", d=data, topics=DsTopics.topics(), chart=json.dumps(chart)
    )


@bp.route("/")
def form():
    now = datetime.datetime.utcnow()
    default_start = now.replace(month=now.month - 1)
    return flask.render_template(
        "dsalerts_form.html",
        cases=DsTopics.cases(),
        now=now,
        default_start=default_start,
    )

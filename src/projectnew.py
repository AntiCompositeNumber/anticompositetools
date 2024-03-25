#!/usr/bin/env python3
# coding: utf-8
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright 2020 AntiCompositeNumber

import flask
import pywikibot
import pywikibot.data.mysql
import pywikibot.data.api
from datetime import timedelta, datetime
from collections import defaultdict
from typing import List, NamedTuple, Iterator, Tuple, Dict

bp = flask.Blueprint("projectnew", __name__, url_prefix="/projectnew")

site = pywikibot.Site("en", "wikipedia")
Article = NamedTuple("Article", [("title", str), ("quality", str), ("author", str)])

# Test if running from Wikimedia Cloud Services (Toolforge)
# If true, a database connection can be assumed
try:
    f = open("/etc/wmcs-project")
except FileNotFoundError:
    wmcs = False
else:
    f.close()
    wmcs = True


def get_new_category_pages(
    category: pywikibot.Category,
    period: timedelta = timedelta(days=-7),
    namespaces: List[int] = [1],
) -> List[Tuple[pywikibot.page.BasePage, datetime]]:
    """Return a list of pages recently added to a category,
    ordered by addition date. Switches between API and DB connection.

    args:
    category -- pywikibot.Category that should be checked

    kwargs:
    period -- negative datetime.timedelta, default timedelta(days=-7)
              pages are listed between (now + period) and now
    namespaces -- list of ints of talk namespaces (default: [1])
    """
    server_day = site.server_time().replace(hour=0, minute=0, second=0, microsecond=0)
    start_time = server_day + period
    end_time = server_day
    try:
        pages = list(
            _db_get_new_category_pages(category, start_time, end_time, namespaces)
        )
    except ConnectionError:
        pages = list(
            _api_get_new_category_pages(category, start_time, end_time, namespaces)
        )

    return pages


def _api_get_new_category_pages(
    category: pywikibot.Category,
    start_time: pywikibot.Timestamp,
    end_time: pywikibot.Timestamp,
    namespaces: List[int],
) -> Iterator[Tuple[pywikibot.page.BasePage, pywikibot.Timestamp]]:
    """Use API to list category pages. Called by get_new_categoryPages()"""
    for row in pywikibot.data.api.ListGenerator(
        "categorymembers",
        site=site,
        cmtitle=category.title(underscore=True, with_ns=True),
        cmprop="title|type|timestamp",
        cmnamespace="|".join(str(n) for n in namespaces),
        cmtype="page",
        cmsort="timestamp",
        cmstart=start_time.isoformat(),
        cmend=end_time.isoformat(),
    ):
        if row.get("type", "page") != "page":
            continue

        yield (
            pywikibot.Page(site, title=row.get("title", ""), ns=row.get("ns", "")),
            pywikibot.Timestamp.fromISOformat(row.get("timestamp")),
        )


def _db_get_new_category_pages(
    category: pywikibot.Category,
    start_time: pywikibot.Timestamp,
    end_time: pywikibot.Timestamp,
    namespaces: List[int],
) -> Iterator[Tuple[pywikibot.page.BasePage, datetime]]:
    """Use DB to list category pages. Called by get_new_categoryPages()"""
    if not wmcs:
        raise ConnectionError

    query = (
        "SELECT page_namespace, page_title, cl_timestamp "
        "FROM "
        "    categorylinks "
        "    JOIN page ON page_id = cl_from "
        "WHERE "
        '    cl_to = "{catname}" AND '
        '    cl_type = "page" AND '
        "    cl_timestamp >= {start_timestamp} AND "
        "    cl_timestamp < {end_timestamp} AND "
        "    page_namespace in ({nslist}) "
        "ORDER BY cl_timestamp "
    ).format(
        catname=category.title(underscore=True, with_ns=False),
        start_timestamp=start_time.totimestampformat(),
        end_timestamp=end_time.totimestampformat(),
        nslist=", ".join(str(n) for n in namespaces),
    )

    for ns, title, ts in pywikibot.data.mysql.mysql_query(query, dbname=site.dbName()):
        yield (
            pywikibot.Page(site, title=title.decode(encoding="utf-8"), ns=ns),
            ts,
        )


def filter_pages(
    pages: List[Tuple[pywikibot.page.BasePage, pywikibot.Timestamp]],
    redirects=False,
    deleted=False,
) -> List[Tuple[pywikibot.page.BasePage, pywikibot.Timestamp]]:

    filtered = []
    for page, ts in pages:
        if page.isTalkPage():
            page = page.toggleTalkPage()

        if not redirects:
            if page.isRedirectPage():
                continue

        if not deleted:
            if not page.exists():
                continue

        filtered.append((page, ts))

    return filtered


def get_article_metadata(page: pywikibot.page.BasePage) -> Article:
    """Returns article creator and content assesment class as a NamedTuple"""
    return Article(
        title=page.title(),
        quality=get_article_quality(page),
        author=page.oldest_revision.user,
    )


def get_article_quality(page: pywikibot.page.BasePage) -> str:
    """Gets the content assement class from a wikiproject template"""
    if not page.isTalkPage():
        page = page.toggleTalkPage()

    classes = []
    valid_classes = {
        "fa": 1,
        "fl": 1,
        "a": 2,
        "ga": 3,
        "b": 4,
        "c": 5,
        "start": 6,
        "stub": 7,
        "list": 8,
        "draft": 8,
    }
    for value in page.templatesWithParams():
        for para in value[1]:
            key, sep, value = para.partition("=")
            if sep and key.lower() == "class" and value.lower() in valid_classes:
                classes.append(value.lower())

    classes = sorted(classes, key=valid_classes.__getitem__)
    if classes:
        return classes[0]
    else:
        return "unassessed"


def main(cat_name: str):
    category = pywikibot.Category(site, cat_name)
    raw_pages = get_new_category_pages(category)
    pages = filter_pages(raw_pages)
    output: Dict[str, List[Article]] = defaultdict(list)

    for page, ts in pages:
        data = get_article_metadata(page)
        date = ts.date().isoformat()
        output[date].append(data)

    return output


@bp.route("/api/json/<category>")
def api_json(category):
    pages = main(category)
    # convert namedtuples to dicts, since jsonify would convert them to tuples
    return flask.jsonify(
        {key: [item._asdict() for item in value] for key, value in pages.items()}
    )


@bp.route("/api/wikitext/<category>")
def api_wikitext(category):
    pages = main(category)

    wikitext = ""
    for date, values in pages.items():
        wikitext += f"'''{date}'''\n"
        for article in values:
            wikitext += (
                "* {{Article status"
                f"|{article.quality}|{article.title}|{article.author}"
                "}}\n"
            )
    return wikitext

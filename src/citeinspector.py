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

import csv
import logging
import time
import urllib.parse
import uuid

import flask
import mwparserfromhell
import requests
from fuzzywuzzy import fuzz

bp = flask.Blueprint("citeinspector", __name__, url_prefix="/citeinspector")


class HandledError(Exception):
    """Exception that have been flashed already

    Attributes:
        orig_type -- Original exception type
        message -- Additional message (optional)
    """

    def __init__(self, orig_type, message=None):
        self.orig_type = orig_type
        self.message = message


def flash(message, category="message"):
    try:
        flask.flash(message, category)
    except RuntimeError:
        print(category + ":", message)


def get_retry(url, session, method="get", output="object", data=None):
    """Make a request for a resource and retry if that doesn't work."""
    headers = {
        "user-agent": "anticompositetools/citeinspector "
        "(https://tools.wmflabs.org/anticompositetools/citeinspector; "
        "tools.anticompositetools@tools.wmflabs.org) python-requests/"
        + requests.__version__
    }

    for i in range(1, 5):  # pragma: no branch
        try:
            if method == "get":
                response = session.get(url, headers=headers)
            elif method == "post":
                response = session.post(url, headers=headers, data=data)
            else:
                raise NotImplementedError

            response.raise_for_status()

            if output == "json":
                output_json = response.json()

        except NotImplementedError:
            raise
        except Exception:
            # TODO: Figure out which exceptions should be caught here.
            if (
                response.status_code in [404, 400]
                or response.text == "upstream request timeout"
            ):

                if output == "object":
                    return response
                else:
                    return None
            elif i == 4:
                raise
            else:
                time.sleep(5 * i)
                continue
        else:
            break

    if output == "json":
        return output_json
    else:
        return response


def get_wikitext(url, session):
    wikitext_url = f"{url}&action=raw"

    request = get_retry(wikitext_url, session)
    if request.status_code == 404:
        flash("That page does not exist.", "danger")
        raise HandledError("404 Client Error")

    else:
        start_time = time.strftime("%Y%m%d%H%M%S", time.gmtime())
        timestruct = time.strptime(
            request.headers["Last-Modified"], "%a, %d %b %Y %H:%M:%S %Z"
        )
        edit_time = time.strftime("%Y%m%d%H%M%S", timestruct)
        return (request.text, (edit_time, start_time))


def get_citoid_template_types(session):
    """Loads template to citoid type mapping from wiki"""
    url = f'{get_page_url("MediaWiki:Citoid-template-type-map.json")[0]}' "&action=raw"
    template_type_map = get_retry(url=url, session=session, output="json")
    supported_templates = [
        template
        for key, template in template_type_map.items()
        if template != "Citation"
    ]

    return template_type_map, supported_templates


def find_refs(code, supported_templates):
    """Find refs in the wikitext"""
    # Check for <ref> tags with citation templates
    for tag in code.ifilter_tags(matches="ref"):
        if tag.contents.filter_templates():
            # Ignore self-closed, unparsable, and empty tags
            cite_data, template_name = grab_cite_data(
                tag.contents.filter_templates()[0], supported_templates
            )
            if cite_data is not None:
                try:
                    # If the reference is already named, use that.
                    ref_id = tag.get("name").value
                except ValueError:
                    # Otherwise, grab a uuid to use in place of the name
                    ref_id = uuid.uuid4()

                yield dict(
                    name=str(ref_id),
                    template=template_name,
                    source="wikitext",
                    location="ref",
                    wikitext=str(tag),
                    data=cite_data,
                )

    # Check for citation templates elsewhere in the text
    for template in code.ifilter_templates(recursive=False):
        cite_data, template_name = grab_cite_data(template, supported_templates)
        if cite_data is not None:
            # We could generate a Harvard anchor here, but I don't trust
            # that to be unique
            ref_id = uuid.uuid4()
            yield dict(
                name=str(ref_id),
                template=template_name,
                source="wikitext",
                location="text",
                wikitext=str(template),
                data=cite_data,
            )


def grab_cite_data(template, supported_templates):
    """Check for supported templates and extract citation data"""
    template_name = str(template.name).lower().strip().capitalize()

    if template_name in supported_templates:
        data = {
            str(para.name).lower().strip(): str(para.value)
            for para in template.params
            if para.value.strip()
        }
        return data, template_name
    else:
        return None, None


def get_bib_ident(cite_data):
    """Return the best identifier (ISBN, DOI, PMID, PMCID, or URL)"""
    data = cite_data["data"]
    return data.get(
        "isbn", data.get("pmcid", data.get("pmid", data.get("doi", data.get("url"))))
    )


def get_citoid_data(ident, session):
    rest_api = "https://en.wikipedia.org/api/rest_v1/"

    url = f"{rest_api}data/citation/mediawiki/{urllib.parse.quote_plus(ident)}"
    data = get_retry(url, session, output="json")
    if data is not None:
        return data[0]
    else:
        return None


def map_citoid_to_templates(
    raw_citoid_data, wikitext_data, templatedata_cache, template_type_map, session
):
    try:
        citoid_template = template_type_map[raw_citoid_data["itemType"]]
    except KeyError:
        return None, templatedata_cache

    try:
        templatedata = templatedata_cache[citoid_template]
    except KeyError:
        templatedata = get_TemplateData_map(citoid_template, session)
        templatedata_cache[citoid_template] = templatedata
    td_map = templatedata["maps"]["citoid"]

    data = {}
    for key, value in raw_citoid_data.items():
        if key == "author":
            for i, author in enumerate(value):
                if i == 0:
                    ordinal = ""
                else:
                    ordinal = str(i + 1)
                last, first = lastnamefirstname(author)
                if last:  # pragma: no branch
                    data[f"last{ordinal}"] = last
                    data[f"first{ordinal}"] = first

        elif key == "editor":
            for i, author in enumerate(value):
                last, first = lastnamefirstname(author)
                if i == 0:
                    ordinal = ""
                else:
                    ordinal = str(i + 1)
                if last:  # pragma: no branch
                    data[f"editor{ordinal}-last"] = last
                    data[f"editor{ordinal}-first"] = first

        elif type(value) is str:
            param = td_map.get(key)
            if param is not None:
                data[param] = value
    return (
        dict(
            name=wikitext_data["name"],
            template=citoid_template,
            template_data=templatedata,
            source=raw_citoid_data.get("source", "[Citoid]")[0],
            location=wikitext_data["location"],
            data=data,
        ),
        templatedata_cache,
    )


def lastnamefirstname(author):
    if author[0] == "":
        if author[1] == "":
            return None, None
        parsed = list(csv.reader([author[1]], skipinitialspace=True))[0]
        if len(parsed) >= 2:
            return parsed[0], parsed[1]
        else:
            return author[1], ""
    else:
        return author[1], author[0]


def get_TemplateData_map(template, session):
    mw_api = "https://en.wikipedia.org/w/api.php"
    request_body = dict(
        action="templatedata", format="json", titles="Template:" + template
    )

    templatedata = get_retry(
        mw_api, session, method="post", output="json", data=request_body
    )
    pages = templatedata["pages"]
    return pages[list(pages)[0]]


def concat_items(wikitext_data, citoid_data):
    """Zip wikitext and citoid data together"""
    cite = {}
    wt_citedata = wikitext_data["data"]
    ct_citedata = citoid_data["data"]
    cite["name"] = wikitext_data["name"]
    if wikitext_data["template"] == citoid_data["template"]:
        cite["template"] = citoid_data["template"]
    else:
        # If the template that's there doesn't match the template that
        # Citoid thinks should be there, the parameters won't match up.
        return None
    cite["citoid_source"] = citoid_data["source"]
    cite["location"] = wikitext_data["location"]
    cite["ratio"] = fuzz_seq(wt_citedata.values(), ct_citedata.values())
    cite["data"] = {}

    templatedata = citoid_data["template_data"]
    keys = list(wt_citedata)
    for key in ct_citedata.copy():
        if key not in keys:
            # Switch key from citoid to param alias used in wikitext
            aliases = templatedata["params"].get(key, {}).get("aliases", [])
            for alias in aliases:
                if alias in keys:
                    ct_citedata[alias] = ct_citedata.pop(key)
                    break
            else:
                keys.append(key)

    for key in keys:
        if key == "access-date":
            # Ignore access date, shouldn't be changed for metadata changes
            continue
        wt_value = wt_citedata.get(key, "")
        ct_value = ct_citedata.get(key, "")
        cite["data"][key] = {
            "wikitext": wt_value,
            "citoid": ct_value,
            "ratio": fuzz_item(wt_value, ct_value),
        }

    cite["wikitext"] = wikitext_data["wikitext"]

    return cite


def fuzz_item(item_a, item_b):
    return fuzz.partial_ratio(item_a, item_b)


def fuzz_seq(set_a, set_b):
    str_a = ""
    str_b = ""
    for item in set_a:
        str_a += item + " "
    for item in set_b:
        str_b += item + " "
    return fuzz.token_set_ratio(str_a, str_b)


def get_page_url(rawinput):
    """Take the user input and get a suitable URL out of it.
    If the input is not a URL, assume it's an en.wp page, since only en.wp is
    supported right now.
    """
    parsed = urllib.parse.urlparse(rawinput)

    site = parsed.netloc
    if "http" not in parsed.scheme:
        # Assume page on enwiki
        title = rawinput
        site = "en.wikipedia.org"
    elif site != "en.wikipedia.org":
        flash("Sorry, but only the English Wikipedia is supported right now", "danger")
        raise ValueError
    elif parsed.path == "/w/index.php":
        query_params = urllib.parse.parse_qs(parsed.query)
        if "oldid" not in query_params:
            title = query_params["title"][0]
        else:
            flash("Invalid URL", "danger")
            raise ValueError
    elif "/wiki/" in parsed.path:
        title = parsed.path[6:]
    else:
        flash("Invalid URL", "danger")
        raise ValueError

    return f"https://{site}/w/index.php?title={title}", title


def citeinspector(url):
    session = requests.Session()
    logging.info("Processing new page: " + url)
    wikitext, times = get_wikitext(url, session)
    template_type_map, supported_templates = get_citoid_template_types(session)

    templatedata_cache = {}
    output = {}
    meta = {}
    found = 0
    code = mwparserfromhell.parse(wikitext)

    for old_data in find_refs(code, supported_templates):
        # we've found citation data, found to at least 1
        if found < 1:
            found = 1

        ident = get_bib_ident(old_data)
        if ident:
            # we've found identifiers, found to at least 2
            if found < 2:
                found = 2
            raw_citoid_data = get_citoid_data(ident.strip(), session)
        else:  # pragma: no cover
            # These lines have tests, but get optomised out by the compiler
            # and therefore missed by coverage
            continue

        if raw_citoid_data is not None:
            # we've got citoid data, set found to at least 3
            if found < 3:
                found = 3
            citoid_data, templatedata_cache = map_citoid_to_templates(
                raw_citoid_data,
                old_data,
                templatedata_cache,
                template_type_map,
                session,
            )
        else:  # pragma: no cover
            continue

        citedata = concat_items(old_data, citoid_data)
        if citedata:
            # citoid and wikitext information were matched
            if found < 4:
                found = 4
            output[old_data["name"]] = citedata
        else:  # pragma: no cover
            continue

    meta["start_time"] = times[1]
    meta["edit_time"] = times[0]
    if found < 4:
        # When found < 4, something wasn't found.
        # Add what should have been found next to meta
        meta["not_found"] = ("refs", "ident", "data", "para")[found]
    session.close()

    return output, wikitext, meta


@bp.route("/", methods=["GET"])
def form():
    return flask.render_template("citeinspector.html")


@bp.route("/output", methods=["POST"])
def output():
    rawinput = flask.request.form["page_url"]
    url, title = get_page_url(rawinput)
    output, wikitext, meta = citeinspector(url)
    meta["url"] = url
    meta["title"] = title
    if len(output):
        return flask.render_template(
            "citeinspector-diff.html", d=output, wikitext=wikitext, meta=meta
        )
    else:
        return flask.render_template("citeinspector-none.html", meta=meta), 404


@bp.route("/concat", methods=["POST"])
def concat():
    data = flask.json.loads(flask.request.form["data"])
    meta = flask.json.loads(flask.request.form["meta"])
    wikitext = flask.request.form["wikitext"]
    code = mwparserfromhell.parse(wikitext)
    changes = {}
    for key, value in flask.request.form.items():
        if key in ["wikitext", "data", "meta"] or value == "":
            continue
        cite_id, sep, para = key.rpartition("/")
        if sep != "/":
            continue
        else:
            if cite_id not in changes:
                changes[cite_id] = {}
            changes[cite_id][para] = value

    for cite_id, cite_data in changes.items():
        cite_obj = code.filter(matches=data[cite_id]["wikitext"])
        for obj in cite_obj:
            if obj != data[cite_id]["wikitext"]:
                continue
            elif type(obj) == mwparserfromhell.nodes.tag.Tag:
                cite_template = obj.contents.filter_templates()[0]
            elif type(obj) == mwparserfromhell.nodes.template.Template:
                cite_template = obj

            for para, value in cite_data.items():
                cite_template.add(para, value)

    submit_url = f'{meta["url"]}&action=submit'
    return flask.render_template(
        "citeinspector-redirect.html",
        submit_url=submit_url,
        newtext=str(code),
        start_time=meta["start_time"],
        edit_time=meta["edit_time"],
    )

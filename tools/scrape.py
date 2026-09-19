#!/usr/bin/env python3
"""
Singapore Pools 4D scraper.

Stdlib only, on purpose: this runs in a GitHub Actions cron with no pip step.

How the site works, since none of it is documented anywhere:

  The draw *index* is a bare <select> served as a static file --

    /DataFileArchive/Lottery/Output/fourd_result_draw_list_en.html

  -- one <option> per draw, back to 2023, carrying the draw number, the date,
  an isCancelled flag, and a `queryString` of the form sppl=<base64>, where the
  base64 decodes to the literal text "DrawNumber=5530". That is the whole
  authentication story: there isn't one.

  A single draw is then

    /en/product/Pages/4d_results.aspx?sppl=...

  Note the path. It used to be /en/product/sr/Pages/ and that now 404s, which
  is the failure mode to expect from this source: not an error, a redirect to a
  200 "page not found". Hence assert_looks_like_results() below -- a silent
  redirect must break the build, not quietly write an empty history.

There is no Access-Control-Allow-Origin on any of it, so the app can never
fetch these directly from the WebView. That is why this exists: it runs on a
schedule, and the app reads the JSON it produces.
"""

import argparse
import base64
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

HOST = "https://www.singaporepools.com.sg"
DRAW_LIST = HOST + "/DataFileArchive/Lottery/Output/fourd_result_draw_list_en.html"
RESULT_PAGE = HOST + "/en/product/Pages/4d_results.aspx?sppl="

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
SGT = timezone(timedelta(hours=8))

# Polite: the site is not ours and a backfill is hundreds of requests.
DELAY_S = 0.4
RETRIES = 3


# ---------------------------------------------------------------- fetching

def fetch(url):
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace"), r.geturl()
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("fetch failed after %d tries: %s (%s)" % (RETRIES, url, last))


def assert_looks_like_results(body, final_url, draw):
    """A moved page returns 200 on an error page rather than a 404. Catch that."""
    if "PageNotFoundError" in final_url:
        raise RuntimeError(
            "redirected to the site's not-found page for draw %s -- the results "
            "URL has moved again; fix RESULT_PAGE in this file" % draw)
    if "drawNumber" not in body:
        raise RuntimeError("no drawNumber anchor in draw %s; the markup changed" % draw)


# ---------------------------------------------------------------- parsing

TAGS = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")


def text_of(fragment):
    return html.unescape(WS.sub(" ", TAGS.sub(" ", fragment))).strip()


def find_all(pattern, body, flags=re.S):
    return re.findall(pattern, body, flags)


def one(pattern, body, what, flags=re.S):
    m = re.search(pattern, body, flags)
    if not m:
        raise RuntimeError("could not find %s" % what)
    return m.group(1)


def parse_draw_list(body):
    """[(draw_number, sppl, date_label, cancelled)] newest first."""
    out = []
    for opt in find_all(r"<option[^>]*>[^<]*</option>", body):
        num = re.search(r"value='(\d+)'", opt)
        qs = re.search(r"queryString='sppl=([^']+)'", opt)
        if not (num and qs):
            continue
        cancelled = bool(re.search(r"isCancelled='(?!')", opt))
        out.append((int(num.group(1)), qs.group(1), text_of(opt), cancelled))
    if not out:
        raise RuntimeError("draw list parsed to nothing; the <select> markup changed")
    return out


def sppl_for(draw_number):
    """The site's own encoding, reproduced so we can request a draw we only know by number."""
    return base64.b64encode(("DrawNumber=%d" % draw_number).encode()).decode()


DATE_RE = re.compile(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})")
MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def iso_date(label):
    m = DATE_RE.search(label)
    if not m:
        raise RuntimeError("unparseable date: %r" % label)
    d, mon, y = m.group(1), m.group(2)[:3].title(), m.group(3)
    return "%s-%02d-%02d" % (y, MONTHS[mon], int(d))


def parse_4d(body):
    date = iso_date(text_of(
        one(r"<th[^>]*class='drawDate'[^>]*>(.*?)</th>", body, "draw date")))
    draw = int(re.sub(r"\D", "", text_of(
        one(r"<th[^>]*class='drawNumber'[^>]*>(.*?)</th>", body, "draw number"))))

    def prize(cls):
        return text_of(one(r"<td[^>]*class='%s'[^>]*>(.*?)</td>" % cls, body, cls))

    def block(cls):
        chunk = one(r"<tbody[^>]*class='%s'[^>]*>(.*?)</tbody>" % cls, body, cls)
        return [text_of(td) for td in find_all(r"<td[^>]*>(.*?)</td>", chunk)
                if re.fullmatch(r"\d{4}", text_of(td))]

    return {
        "draw": draw,
        "date": date,
        "first": prize("tdFirstPrize"),
        "second": prize("tdSecondPrize"),
        "third": prize("tdThirdPrize"),
        "starter": block("tbodyStarterPrizes"),
        "consolation": block("tbodyConsolationPrizes"),
    }


# ---------------------------------------------------------------- driver

def scrape(limit, known):
    """Fetch up to `limit` draws not already in `known` (a set of draw numbers)."""
    body, _ = fetch(DRAW_LIST)
    index = parse_draw_list(body)
    picked = []
    for number, sppl, label, cancelled in index:
        if len(picked) >= limit:
            break
        if number in known:
            continue
        if cancelled:
            print("  skip draw %d (cancelled)" % number, file=sys.stderr)
            continue
        picked.append((number, sppl))

    out = []
    for i, (number, sppl) in enumerate(picked, 1):
        page, final = fetch(RESULT_PAGE + sppl)
        assert_looks_like_results(page, final, number)
        try:
            out.append(parse_4d(page))
        except RuntimeError as e:
            # One malformed draw must not sink a backfill of hundreds.
            print("  WARN draw %d: %s" % (number, e), file=sys.stderr)
        if i % 25 == 0 or i == len(picked):
            print("  %d/%d" % (i, len(picked)), file=sys.stderr)
        time.sleep(DELAY_S)
    return out


def merge(existing, fresh):
    by_draw = {d["draw"]: d for d in existing}
    by_draw.update({d["draw"]: d for d in fresh})
    return sorted(by_draw.values(), key=lambda d: d["draw"], reverse=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="data/history.json")
    ap.add_argument("--limit", type=int, default=5,
                    help="max NEW draws (default 5, the incremental cron case)")
    ap.add_argument("--backfill", type=int, metavar="N",
                    help="shorthand for --limit N on a cold start")
    args = ap.parse_args()
    if args.backfill:
        args.limit = args.backfill

    prev = {"fourd": []}
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as f:
            prev = json.load(f)

    known = {d["draw"] for d in prev.get("fourd", [])}
    fourd = merge(prev.get("fourd", []), scrape(args.limit, known))

    payload = {
        "generated": datetime.now(SGT).isoformat(timespec="seconds"),
        "source": "singaporepools.com.sg",
        "fourd": fourd,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    print("wrote %s: %d draws" % (args.out, len(fourd)))
    if fourd:
        print("  newest %s draw %d  1st=%s" % (fourd[0]["date"], fourd[0]["draw"], fourd[0]["first"]))


if __name__ == "__main__":
    main()

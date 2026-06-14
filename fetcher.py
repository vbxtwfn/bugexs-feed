#!/usr/bin/env python3
import urllib.request, urllib.error, json, re, os, sys
from datetime import datetime
from urllib.parse import urljoin

BASE_URL = "https://m.bugexs.com"

def fetch(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cache-Control": "no-cache",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            ct = resp.headers.get("Content-Type", "")
            print(f"DEBUG: {url} -> {resp.status}, {ct[:30]}, {resp.headers.get('Content-Length','?')} bytes", file=sys.stderr)
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"DEBUG: HTTP {e.code} {e.reason}", file=sys.stderr)
        return f"ERROR:{e.code}"
    except Exception as e:
        print(f"DEBUG: {type(e).__name__}: {e}", file=sys.stderr)
        return f"ERROR:{e}"

def find_real_gt(s, start, end):
    i, in_quote = start, False
    while i < end:
        c = s[i]
        if c == '"': in_quote = not in_quote
        elif c == ">" and not in_quote: return i
        i += 1
    return -1

def parse_cover_cards(html):
    results = []
    for url_m in re.finditer(r'data-original="([^"]+)"', html):
        url, pos = url_m.group(1), url_m.end()
        next_a = html.find('<a class="tit"', pos)
        if next_a == -1: break
        gt_pos = find_real_gt(html, pos, next_a)
        if gt_pos == -1: continue
        a_m = re.search(r'<a[^>]*class="tit"[^>]*href="(/article/\d+\.html)"[^>]*>([^<]+)</a>', html[next_a:])
        if not a_m: continue
        href, title = a_m.group(1), a_m.group(2)
        li_start = html.rfind("<li", 0, url_m.start())
        li_end = html.find("</li>", next_a)
        if li_start == -1 or li_end == -1: continue
        li_block = html[li_start:li_end+5]
        intro_m = re.search(r'<p class="intro">(.*?)</p>', li_block, re.DOTALL)
        intro = re.sub(r'\s+', ' ', intro_m.group(1).strip()) if intro_m else ""
        author, cat = "", ""
        info_m = re.search(r'<p class="info">(.*?)</p>', li_block, re.DOTALL)
        if info_m:
            am = re.search(r'作者：</aria>([^<]+)', info_m.group(1))
            if am: author = am.group(1).strip()
            cm = re.search(r'<em[^>]*>([^<]+)</em>', info_m.group(1))
            if cm: cat = cm.group(1).strip()
        results.append({"title": title.strip(), "author": author, "category": cat,
                        "url": urljoin(BASE_URL, href), "cover": url.strip(),
                        "intro": intro, "source": "bugexs"})
    return results

def parse_home(html):
    results = []
    for block in re.findall(r'<div class="book-slide">.*?<ul[^>]*>(.*?)</ul>.*?</div>', html, re.DOTALL):
        for url, cover, title, author in re.findall(
            r'<a href="(/article/\d+\.html)"[^>]*>\s*'
            r'<img[^>]*?data-original="([^"]+)"[^>]*/>\s*'
            r'<span[^>]*>([^<]+)</span>\s*'
            r'<em[^>]*>[^：]+：([^<]+)</em>', block, re.DOTALL):
            results.append({"title": title.strip(), "author": author.strip(),
                            "url": urljoin(BASE_URL, url), "cover": cover.strip(), "source": "bugexs"})
    for block in re.findall(r'<ul class="vlist">(.*?)</ul>', html, re.DOTALL):
        for url, time, author, title in re.findall(
            r'<a href="(/article/\d+\.html)"[^>]*>\s*<span[^>]*>(\[[\d:]+\])</span>'
            r'\s*<p class="author">([^<]+)</p>\s*<p>([^<]+)</p>', block):
            results.append({"title": title.strip(), "author": author.strip(),
                            "url": urljoin(BASE_URL, url), "cover": "", "intro": "",
                            "category": "", "updated_at": time.strip(), "source": "bugexs"})
    seen, unique = set(), []
    for item in results:
        if item["url"] not in seen:
            seen.add(item["url"]); unique.append(item)
    return unique

def make_feed(name, feed_type, url, parser):
    print(f"Fetching {name}...", file=sys.stderr)
    html = fetch(url)
    if html.startswith("ERROR:"):
        print(f"FAILED: {html}", file=sys.stderr)
        return None
    items = parser(html)
    print(f"  -> {len(items)} items", file=sys.stderr)
    return {"version": "https://jsonfeed.org/version/1.1",
            "title": f"不格小说网 - {name}",
            "home_page_url": BASE_URL,
            "generated_at": datetime.now().isoformat(),
            "feed_type": feed_type, "feed_name": name,
            "total_items": len(items), "items": items}

os.makedirs("feeds", exist_ok=True)
for name, ft, url in [("最近更新","lastupdate",f"{BASE_URL}/all/lastupdate_1.html"),
                        ("月推荐榜","monthvote",f"{BASE_URL}/all/monthvote_1.html"),
                        ("日点击榜","dayvisit",f"{BASE_URL}/all/dayvisit_1.html"),
                        ("周推荐榜","weekvote",f"{BASE_URL}/all/weekvote_1.html")]:
    f = make_feed(name, ft, url, parse_cover_cards)
    if f:
        with open(f"feeds/{ft}.json","w") as fp: json.dump(f, fp, ensure_ascii=False, indent=2)

f = make_feed("首页","home",BASE_URL+"/", parse_home)
if f:
    with open("feeds/home.json","w") as fp: json.dump(f, fp, ensure_ascii=False, indent=2)

print("Done!", file=sys.stderr)

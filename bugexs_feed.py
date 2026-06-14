#!/usr/bin/env python3
"""
不格小说网 JSON Feed 生成器
抓取 m.bugexs.com 并生成 JSON Feed，供阅读 App 订阅使用

用法:
  python3 bugexs_feed.py                          # 最近更新 JSON
  python3 bugexs_feed.py -t monthvote -o feed.json  # 月推荐榜
  python3 bugexs_feed.py -t home -o feed.json       # 首页（轮播+最近更新）
  python3 bugexs_feed.py --serve 8080               # 启动 HTTP 服务
"""

import json
import re
import sys
import argparse
import requests
import bs4
from datetime import datetime
from urllib.parse import urljoin


BASE_URL = "https://m.bugexs.com"


def fetch(url: str) -> str:
    """使用 requests 拉取页面"""
    resp = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.text


def find_real_gt(s: str, start: int, end: int) -> int:
    """在 [start, end) 范围内找第一个不在引号内的 >"""
    i = start
    in_quote = False
    while i < end:
        c = s[i]
        if c == '"':
            in_quote = not in_quote
        elif c == ">" and not in_quote:
            return i
        i += 1
    return -1


def parse_vlist(html: str) -> list:
    """
    解析首页最近更新竖排列表
    格式: <ul class="vlist"><li><a href="..."><span>[时间]</span><p class="author">作者</p><p>标题</p></a></li>...
    """
    results = []
    for block in re.findall(r'<ul class="vlist">(.*?)</ul>', html, re.DOTALL):
        items = re.findall(
            r'<a href="(/article/\d+\.html)"[^>]*>\s*<span[^>]*>(\[[\d:]+\])</span>'
            r'\s*<p class="author">([^<]+)</p>\s*<p>([^<]+)</p>',
            block
        )
        for url, time, author, title in items:
            results.append({
                "title": title.strip(),
                "author": author.strip(),
                "url": urljoin(BASE_URL, url),
                "cover": "",
                "intro": "",
                "category": "",
                "updated_at": time.strip(),
                "source": "bugexs",
            })
    return results


def parse_cover_cards(html: str) -> list:
    """
    解析书库封面卡片列表
    HTML 格式（img 标签的 > 在 alt 属性值中）：
    <li>
      <img class="pic lazy" data-original="https://..." alt="...">   ← 这里的 > 是属性值的一部分
      <a class="tit" href="/article/123.html">标题</a>                  ← 真正的标签关闭
      <p class="intro">简介...</p>
      <p class="info"><span><aria>作者：</aria>作者名</span><em class="type">分类</em></p>
    </li>
    """
    results = []

    for url_m in re.finditer(r'data-original="([^"]+)"', html):
        url = url_m.group(1)
        pos = url_m.end()

        # 找后面的 <a class="tit"
        next_a = html.find('<a class="tit"', pos)
        if next_a == -1:
            break

        # 找 img 标签真正的关闭 >（不在引号内）
        gt_pos = find_real_gt(html, pos, next_a)
        if gt_pos == -1:
            continue

        # 提取 <a class="tit" href="...">Title</a>
        a_m = re.search(
            r'<a[^>]*class="tit"[^>]*href="(/article/\d+\.html)"[^>]*>([^<]+)</a>',
            html[next_a:]
        )
        if not a_m:
            continue

        href, title = a_m.group(1), a_m.group(2)

        # 获取整个 <li>...</li> 块（包含 intro 和 info）
        li_start = html.rfind("<li", 0, url_m.start())
        li_end = html.find("</li>", next_a)
        if li_start == -1 or li_end == -1:
            continue

        li_block = html[li_start:li_end + 5]

        # 简介
        intro_m = re.search(r'<p class="intro">(.*?)</p>', li_block, re.DOTALL)
        intro = re.sub(r'\s+', ' ', intro_m.group(1).strip()) if intro_m else ""

        # 作者和分类
        author, cat = "", ""
        info_m = re.search(r'<p class="info">(.*?)</p>', li_block, re.DOTALL)
        if info_m:
            # 作者格式: <aria>作者：</aria>名字
            am = re.search(r'作者：</aria>([^<]+)', info_m.group(1))
            if am:
                author = am.group(1).strip()
            # 分类: <em class="type">分类名</em>
            cm = re.search(r'<em[^>]*>([^<]+)</em>', info_m.group(1))
            if cm:
                cat = cm.group(1).strip()

        results.append({
            "title": title.strip(),
            "author": author,
            "category": cat,
            "url": urljoin(BASE_URL, href),
            "cover": url.strip(),
            "intro": intro,
            "source": "bugexs",
        })

    return results


def parse_slide(html: str) -> list:
    """
    解析首页轮播推荐
    格式: <li><a href="..."><img data-original="..."/><span>标题</span><em>作者：xxx</em></a></li>
    """
    results = []
    for block in re.findall(r'<div class="book-slide">.*?<ul[^>]*>(.*?)</ul>.*?</div>', html, re.DOTALL):
        items = re.findall(
            r'<a href="(/article/\d+\.html)"[^>]*>\s*'
            r'<img[^>]*?data-original="([^"]+)"[^>]*/>\s*'
            r'<span[^>]*>([^<]+)</span>\s*'
            r'<em[^>]*>[^：]+：([^<]+)</em>',
            block, re.DOTALL
        )
        for url, cover, title, author in items:
            results.append({
                "title": title.strip(),
                "author": author.strip(),
                "url": urljoin(BASE_URL, url),
                "cover": cover.strip(),
                "source": "bugexs",
            })
    return results


def generate_feed(feed_type: str = "lastupdate", page: int = 1) -> dict:
    """生成指定类型的 JSON Feed"""

    type_urls = {
        "lastupdate": f"{BASE_URL}/all/lastupdate_{page}.html",
        "monthvote":  f"{BASE_URL}/all/monthvote_{page}.html",
        "dayvote":    f"{BASE_URL}/all/dayvote_{page}.html",
        "weekvote":   f"{BASE_URL}/all/weekvote_{page}.html",
        "dayvisit":   f"{BASE_URL}/all/dayvisit_{page}.html",
        "weekvisit":  f"{BASE_URL}/all/weekvisit_{page}.html",
        "monthvisit": f"{BASE_URL}/all/monthvisit_{page}.html",
        "allvisit":   f"{BASE_URL}/all/allvisit_{page}.html",
        "hot":        f"{BASE_URL}/hot/",
        "all":        f"{BASE_URL}/all/",
        "postdate":   f"{BASE_URL}/all/postdate_{page}.html",
        "home":       f"{BASE_URL}/",
    }

    type_names = {
        "lastupdate": "最近更新",
        "monthvote":  "月推荐榜",
        "dayvote":    "日推荐榜",
        "weekvote":   "周推荐榜",
        "dayvisit":   "日点击榜",
        "weekvisit":  "周点击榜",
        "monthvisit": "月点击榜",
        "allvisit":   "总点击榜",
        "hot":        "热门推荐",
        "all":        "全部分类",
        "postdate":   "最新入库",
        "home":       "首页",
    }

    url = type_urls.get(feed_type, type_urls["lastupdate"])
    name = type_names.get(feed_type, "小说")

    print(f"📡 抓取: {url}", file=sys.stderr)
    html = fetch(url)

    # 解析不同结构
    if feed_type == "home":
        items = parse_slide(html) + parse_vlist(html)
    else:
        items = parse_cover_cards(html)

    # 去重（按 url）
    seen = set()
    unique = []
    for item in items:
        key = item["url"]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    print(f"📚 解析到 {len(unique)} 本书", file=sys.stderr)

    return {
        "version": "https://jsonfeed.org/version/1.1",
        "title": f"不格小说网 - {name}",
        "home_page_url": BASE_URL,
        "feed_url": f"{BASE_URL}/feed/{feed_type}.json",
        "description": "好看的小说推荐，免费在线阅读",
        "generated_at": datetime.now().isoformat(),
        "feed_type": feed_type,
        "feed_name": name,
        "page": page,
        "source_url": url,
        "total_items": len(unique),
        "items": unique,
    }


# ── HTTP 服务 ───────────────────────────────────────────────

def serve(port: int = 8080):
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {fmt % args}", file=sys.stderr)

        def do_GET(self):
            path = self.path.rstrip("/")
            if path == "/" or path == "":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(HTTP_INDEX.encode())
                return
            if path.startswith("/feed/"):
                ft = path.replace("/feed/", "").replace(".json", "") or "lastupdate"
                try:
                    feed = generate_feed(ft)
                    data = json.dumps(feed, ensure_ascii=False, indent=2)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Cache-Control", "max-age=600")
                    self.end_headers()
                    self.wfile.write(data.encode("utf-8"))
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self.send_response(500)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(str(e).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

    HTTP_INDEX = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>不格小说网 Feed</title>
<style>body{font-family:-apple-system,sans-serif;padding:2rem;max-width:600px;margin:0 auto}
h1{color:#222}li{margin:.5rem 0}a{color:#4a90e2;text-decoration:none}a:hover{text-decoration:underline}
code{background:#f5f5f5;padding:.2rem .5rem;border-radius:4px}</style>
</head><body>
<h1>📚 不格小说网 JSON Feed</h1>
<p>可用端点:</p>
<ul>
<li><a href="/feed/home.json">首页（轮播+最近更新）</a></li>
<li><a href="/feed/lastupdate.json">最近更新</a></li>
<li><a href="/feed/monthvote.json">月推荐榜</a></li>
<li><a href="/feed/weekvote.json">周推荐榜</a></li>
<li><a href="/feed/dayvisit.json">日点击榜</a></li>
<li><a href="/feed/weekvisit.json">周点击榜</a></li>
<li><a href="/feed/postdate.json">最新入库</a></li>
<li><a href="/feed/hot.json">热门推荐</a></li>
</ul>
<p>示例调用:</p>
<pre>curl http://localhost:""" + str(port) + """/feed/lastupdate.json | jq .</pre>
</body></html>"""

    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"\n🚀 不格小说网 Feed 服务已启动", file=sys.stderr)
    print(f"   http://0.0.0.0:{port}/feed/lastupdate.json", file=sys.stderr)
    print(f"   停止: Ctrl+C\n", file=sys.stderr)
    server.serve_forever()


# ── CLI 入口 ───────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="不格小说网 JSON Feed 生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Feed 类型:
  home        首页（轮播推荐 + 最近更新）
  lastupdate  最近更新
  monthvote   月推荐榜
  weekvote    周推荐榜
  dayvisit    日点击榜
  weekvisit   周点击榜
  postdate    最新入库
  hot         热门推荐

示例:
  python3 bugexs_feed.py -t lastupdate -o feed.json
  python3 bugexs_feed.py -t home
  python3 bugexs_feed.py --serve 8080
        """,
    )
    parser.add_argument("-t", "--type",
                        default="lastupdate",
                        choices=["home","lastupdate","monthvote","dayvisit","weekvisit",
                                 "monthvisit","allvisit","dayvote","weekvote","hot",
                                 "all","postdate"],
                        help="Feed 类型")
    parser.add_argument("-p", "--page", type=int, default=1, help="页码")
    parser.add_argument("-o", "--output", help="输出到文件")
    parser.add_argument("--serve", type=int, metavar="PORT", help="启动 HTTP 服务")
    args = parser.parse_args()

    if args.serve:
        serve(args.serve)
    else:
        feed = generate_feed(args.type, args.page)
        output = json.dumps(feed, ensure_ascii=False, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"✅ 已保存: {args.output}", file=sys.stderr)
        else:
            print(output)

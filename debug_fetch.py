#!/usr/bin/env python3
import urllib.request, json

url = "https://m.bugexs.com/all/lastupdate_1.html"
headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        content = resp.read().decode("utf-8", errors="replace")
        print(f"Status: {resp.status}, Length: {len(content)}")
        # Save to file for debugging
        with open("debug_output.txt", "w") as f:
            f.write(content[:5000])
        print("Saved first 5000 chars to debug_output.txt")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} {e.reason}")
    print(e.read().decode()[:500])
except Exception as e:
    print(f"Error: {e}")

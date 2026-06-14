#!/usr/bin/env python3
import urllib.request, urllib.error, json, os, glob, datetime

token = os.environ.get('GITHUB_TOKEN', '')
repo = os.environ.get('REPO', os.environ.get('GITHUB_REPOSITORY', ''))
api = f"https://api.github.com/repos/{repo}"

def api_call(method, url, data=None):
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode())
        raise Exception(f"API Error {e.code}: {body.get('message', body)}")

ref = api_call("GET", f"{api}/git/ref/heads/gh-pages")
commit_sha = ref["object"]["sha"]
print(f"Current gh-pages: {commit_sha[:7]}")

existing_tree = api_call("GET", f"{api}/git/trees/{commit_sha}?recursive=1")

tree_items = []
for item in existing_tree.get('tree', []):
    if item['path'].startswith('.github/'):
        tree_items.append({
            "path": item['path'],
            "mode": item['mode'],
            "type": item['type'],
            "sha": item['sha']
        })

for fpath in sorted(glob.glob("feeds/*.json")):
    fname = os.path.basename(fpath)
    with open(fpath) as f:
        content = f.read()
    blob = api_call("POST", f"{api}/git/blobs",
        json.dumps({"content": content, "encoding": "utf-8"}).encode()
    )
    tree_items.append({
        "path": f"feeds/{fname}",
        "mode": "100644",
        "type": "blob",
        "sha": blob["sha"]
    })
    print(f"  + feeds/{fname}")

new_tree = api_call("POST", f"{api}/git/trees",
    json.dumps({"tree": tree_items, "base_tree": commit_sha}).encode()
)

new_commit = api_call("POST", f"{api}/git/commits",
    json.dumps({
        "message": f"Update feeds {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "tree": new_tree["sha"],
        "parents": [commit_sha]
    }).encode()
)

api_call("PATCH", f"{api}/git/refs/heads/gh-pages",
    json.dumps({"sha": new_commit["sha"]}).encode()
)

print(f"Done! {new_commit['sha'][:7]}")

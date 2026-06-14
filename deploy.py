#!/usr/bin/env python3
import urllib.request, urllib.error, json, os, glob, datetime, time

token = os.environ.get('GITHUB_TOKEN', '')
repo = os.environ.get('REPO', os.environ.get('GITHUB_REPOSITORY', ''))
api = f"https://api.github.com/repos/{repo}"

def api_call(method, url, data=None, max_retries=2):
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

# Get current gh-pages ref
ref = api_call("GET", f"{api}/git/ref/heads/gh-pages")
base_sha = ref["object"]["sha"]
print(f"Current gh-pages: {base_sha[:7]}")

# Get existing tree
existing_tree = api_call("GET", f"{api}/git/trees/{base_sha}?recursive=1")

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
    if fname.startswith('__'):
        print(f"  Skip debug file: {fname}")
        continue
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

# Create new tree
new_tree = api_call("POST", f"{api}/git/trees",
    json.dumps({"tree": tree_items, "base_tree": base_sha}).encode()
)
print(f"New tree: {new_tree['sha'][:7]}")

# Create commit
new_commit = api_call("POST", f"{api}/git/commits",
    json.dumps({
        "message": f"Update feeds {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "tree": new_tree["sha"],
        "parents": [base_sha]
    }).encode()
)
print(f"Commit: {new_commit['sha'][:7]}")

# Update ref with retry (race condition protection)
success = False
for attempt in range(3):
    try:
        # Re-fetch ref SHA to avoid race condition
        latest_ref = api_call("GET", f"{api}/git/ref/heads/gh-pages")
        latest_sha = latest_ref["object"]["sha"]
        
        # Update the commit's first parent to the latest
        if latest_sha != base_sha:
            print(f"  Ref changed from {base_sha[:7]} to {latest_sha[:7]}, retrying...")
            base_sha = latest_sha
            # Re-create tree with new base
            new_tree2 = api_call("POST", f"{api}/git/trees",
                json.dumps({"tree": tree_items, "base_tree": base_sha}).encode()
            )
            new_commit2 = api_call("POST", f"{api}/git/commits",
                json.dumps({
                    "message": f"Update feeds (retry) {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                    "tree": new_tree2["sha"],
                    "parents": [base_sha]
                }).encode()
            )
            api_call("PATCH", f"{api}/git/refs/heads/gh-pages",
                json.dumps({"sha": new_commit2["sha"]}).encode()
            )
        else:
            api_call("PATCH", f"{api}/git/refs/heads/gh-pages",
                json.dumps({"sha": new_commit["sha"]}).encode()
            )
        
        success = True
        print(f"Done! {new_commit['sha'][:7]}")
        break
    except Exception as e:
        print(f"  Attempt {attempt+1} failed: {e}")
        if attempt < 2:
            time.sleep(2)
        else:
            raise

if not success:
    print("ERROR: Failed to update gh-pages after 3 attempts")
    exit(1)

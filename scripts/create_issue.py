#!/usr/bin/env python3
"""Create a GitHub issue reporting missing images (reads missing.json).

Uses env vars: GITHUB_TOKEN, REPO, ISSUE_LABELS, ISSUE_ASSIGNEES, GITHUB_SERVER_URL, GITHUB_RUN_ID
"""
import json
import os
import sys
import urllib.request


def main() -> int:
    token = os.environ.get('GITHUB_TOKEN')
    repo = os.environ.get('REPO')
    missing_file = 'missing.json'
    labels = os.environ.get('ISSUE_LABELS', '')
    assignees = os.environ.get('ISSUE_ASSIGNEES', '')
    run_url = f"{os.environ.get('GITHUB_SERVER_URL','https://github.com')}/{repo}/actions/runs/{os.environ.get('GITHUB_RUN_ID','')}"

    if not token:
        print('No GITHUB_TOKEN; cannot create issue')
        return 0
    if not os.path.exists(missing_file):
        print('No missing.json; nothing to report')
        return 0

    missing = json.load(open(missing_file))
    if not missing:
        print('No missing entries; nothing to report')
        return 0

    title = 'CI: Missing public images in gallery'
    body = 'The CI smoke test detected missing public images.\n\nRun: ' + run_url + '\n\n' + json.dumps(missing, indent=2)
    payload = {'title': title, 'body': body}
    if labels:
        payload['labels'] = [l.strip() for l in labels.split(',') if l.strip()]
    if assignees:
        payload['assignees'] = [a.strip() for a in assignees.split(',') if a.strip()]

    data = json.dumps(payload).encode()
    req = urllib.request.Request(f'https://api.github.com/repos/{repo}/issues', data=data, headers={
        'Authorization': f'token {token}', 'Content-Type': 'application/json', 'User-Agent': 'ci-script'
    })
    try:
        resp = urllib.request.urlopen(req)
        print('Created issue, status', resp.status)
    except Exception as e:
        print('Failed to create issue', e)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

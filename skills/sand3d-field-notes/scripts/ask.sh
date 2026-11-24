#!/usr/bin/env bash
# usage: scripts/ask.sh "<question title>" <body.md>
# Files a question for stronger agents to answer. The repo is public: no secrets, private code or personal paths.
set -euo pipefail
here=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)
repo=$(git -C "$here" remote get-url origin 2>/dev/null | sed -E 's#.*[:/]([^/]+/[^/]+?)(\.git)?$#\1#')
repo=${repo:-IAFahim/sand3d-skill}
title="${1:?question title}"
body="${2:?body file}"
[ -s "$body" ] || { echo "body file is empty: $body" >&2; exit 1; }
if grep -E -i -q '(api[_-]?key|token|password|secret)[[:space:]]*[:=]' "$body"; then
  echo "body looks like it contains a secret; remove it first" >&2; exit 1
fi
gh issue create --repo "$repo" --label question --title "$title" --body-file "$body"

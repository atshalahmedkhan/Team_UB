#!/usr/bin/env bash
# Push docs/wiki/*.md to the GitHub Wiki for this repository.
# Requires: git, push access to the repo wiki.
#
# Usage:
#   ./scripts/sync-wiki.sh
#   WIKI_REMOTE=https://github.com/you/Team_UB.wiki.git ./scripts/sync-wiki.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${ROOT}/docs/wiki"
REMOTE="${WIKI_REMOTE:-}"

if [[ -z "${REMOTE}" ]]; then
  origin="$(git -C "${ROOT}" config --get remote.origin.url 2>/dev/null || true)"
  if [[ "${origin}" =~ github\.com[:/]([^/]+)/([^/.]+) ]]; then
    REMOTE="https://github.com/${BASH_REMATCH[1]}/${BASH_REMATCH[2]%.git}.wiki.git"
  else
    echo "Set WIKI_REMOTE to your repo's wiki clone URL (e.g. https://github.com/org/Team_UB.wiki.git)" >&2
    exit 1
  fi
fi

WORKDIR="$(mktemp -d)"
trap 'rm -rf "${WORKDIR}"' EXIT

echo "Cloning wiki from ${REMOTE} ..."
if git clone "${REMOTE}" "${WORKDIR}/wiki" 2>/dev/null; then
  :
else
  echo "Wiki repo empty or missing — initializing ..."
  mkdir -p "${WORKDIR}/wiki"
  git -C "${WORKDIR}/wiki" init -b main
  git -C "${WORKDIR}/wiki" remote add origin "${REMOTE}"
fi

echo "Copying markdown from ${SRC} ..."
# Do not use rsync --delete: it would remove the wiki clone's .git directory.
find "${SRC}" -maxdepth 1 -name '*.md' -exec cp {} "${WORKDIR}/wiki/" \;

cd "${WORKDIR}/wiki"
git add -A
if git diff --staged --quiet; then
  echo "Wiki already up to date."
  exit 0
fi

git commit -m "Sync wiki from docs/wiki"
git push -u origin HEAD
echo "Wiki published: ${REMOTE%.git}"

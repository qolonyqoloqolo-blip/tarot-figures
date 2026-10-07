#!/bin/zsh
# 公開済みの記事の図だけを img/ にそろえ（build.py）、変更があれば commit して GitHub Pages に push する。
# 許可の確認なしで動かすため、settings.json の permissions.allow と sandbox.excludedCommands にこのスクリプトだけを登録している。
set -e
REPO="$HOME/threads-images"
"$HOME/note-sns-poster/.venv/bin/python" "$REPO/build.py"
git -C "$REPO" add -A
if git -C "$REPO" diff --cached --quiet; then
  echo "変更なし"
  exit 0
fi
git -C "$REPO" commit -q -m "Update figures ($(date +%Y-%m-%d))"
git -C "$REPO" push -q origin main
echo "pushed: $(git -C "$REPO" log --oneline -1)"

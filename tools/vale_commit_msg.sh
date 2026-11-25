#!/bin/sh
# Strip git interactive comments, scissors diffs, and trailers before running Vale (#727).
set -eu

mode=$(git config --get commit.cleanup || printf default)
if [ "$mode" = "default" ]; then
  if [ "${GIT_EDITOR:-}" = ":" ]; then
    mode="whitespace"
  else
    mode="strip"
  fi
fi

case "$mode" in
  verbatim)
    filtered=$(cat "$1")
    ;;
  whitespace)
    filtered=$(git stripspace <"$1")
    ;;
  scissors)
    raw=$(sed -n -e "/------------------------ >8 ------------------------/q" -e "p" "$1")
    filtered=$(printf "%s\n" "$raw" | git stripspace)
    ;;
  *)
    raw=$(sed -n -e "/------------------------ >8 ------------------------/q" -e "p" "$1")
    filtered=$(printf "%s\n" "$raw" | git stripspace --strip-comments)
    ;;
esac

printf "%s\n" "$filtered" \
  | sed -e "/^[A-Za-z-]*-by: /d" \
  | vale --output=line --minAlertLevel=error --path=COMMIT_EDITMSG

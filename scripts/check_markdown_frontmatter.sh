#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCS_DIR="$ROOT/docs"
errors=0

check_file() {
  local file="$1"
  local rel="${file#"$ROOT/"}"

  local first_line
  first_line=$(head -n1 "$file")

  if [[ "$first_line" != "---" ]]; then
    echo "- $rel: missing YAML frontmatter at top of file"
    ((errors++))
    return
  fi

  local closing
  closing=$(awk 'NR>1 && /^---$/{print NR; exit}' "$file")

  if [[ -z "$closing" ]]; then
    echo "- $rel: frontmatter is missing closing '---' delimiter"
    ((errors++))
    return
  fi

  local fm
  fm=$(head -n "$((closing - 1))" "$file" | tail -n "$((closing - 2))")

  for key in when_to_read summary last_updated; do
    if ! echo "$fm" | grep -q "^${key}:"; then
      echo "- $rel: missing required frontmatter key '$key'"
      ((errors++))
    fi
  done

  local summary_val
  summary_val=$(echo "$fm" | grep '^summary:' | sed 's/^summary:[[:space:]]*//' | sed 's/^"//' | sed 's/"$//')
  if [[ -z "$summary_val" ]]; then
    echo "- $rel: frontmatter key 'summary' must be a non-empty string"
    ((errors++))
  fi

  local date_val
  date_val=$(echo "$fm" | grep '^last_updated:' | sed 's/^last_updated:[[:space:]]*//' | sed 's/^"//' | sed 's/"$//')
  if ! [[ "$date_val" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "- $rel: frontmatter key 'last_updated' must be a YYYY-MM-DD string"
    ((errors++))
  fi

  local wtr_inline wtr_list
  wtr_inline=$(echo "$fm" | grep '^when_to_read:' | sed 's/^when_to_read:[[:space:]]*//')
  wtr_list=$(echo "$fm" | grep -c '^  - ' || true)
  if [[ -z "$wtr_inline" ]] && [[ "$wtr_list" -eq 0 ]]; then
    echo "- $rel: frontmatter key 'when_to_read' must be a non-empty string or list of non-empty strings"
    ((errors++))
  fi
}

for md in "$ROOT"/*.md; do
  base=$(basename "$md")
  [[ "$base" == "AGENTS.md" ]] && continue
  check_file "$md"
done

while IFS= read -r -d '' md; do
  check_file "$md"
done < <(find "$DOCS_DIR" -name '*.md' -type f -print0 | sort -z)

if [[ "$errors" -eq 0 ]]; then
  echo "All repo-root/docs markdown files have required frontmatter."
  exit 0
else
  echo "Markdown frontmatter validation failed ($errors error(s))"
  exit 1
fi

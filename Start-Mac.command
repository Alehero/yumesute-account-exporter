#!/bin/zsh
cd -- "${0:A:h}" || exit 1
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  echo 'Install uv first: https://docs.astral.sh/uv/getting-started/installation/'
  echo 'If you have Homebrew: brew install uv'
  read '?Press Enter to close.'
  exit 1
fi
uv run --locked --python 3.12 python launcher.py "$@"
read '?Press Enter to close.'

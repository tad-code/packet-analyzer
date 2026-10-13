#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
    echo
    echo "  Environnement Python introuvable : .venv/bin/python"
    echo "  Creez-le d'abord :"
    echo
    echo "      python3 -m venv .venv"
    echo "      .venv/bin/python -m pip install -r requirements.txt"
    echo
    exit 1
fi

export HOST="${HOST:-0.0.0.0}"

echo
echo "  Analyseur reseau"
echo "  ----------------"

if [ "$(id -u)" -ne 0 ]; then
    if ! command -v getcap >/dev/null 2>&1 || ! getcap "$(readlink -f .venv/bin/python)" 2>/dev/null | grep -q cap_net_raw; then
        echo
        echo "  Note : la capture de paquets exige les droits root, ou la capacite"
        echo "  cap_net_raw sur l'interpreteur. Sans cela, l'application demarre mais"
        echo "  la page Capture expliquera ce qui manque."
    fi
fi

exec .venv/bin/python app.py

#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
python3 main.py
read -p "Нажми Enter для выхода..."
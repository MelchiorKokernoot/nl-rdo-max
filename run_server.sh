#!/bin/bash
[[ -d .venv ]] && source .venv/bin/activate

#uvicorn inge6.main:app --reload --host 0.0.0.0 --port 8006
python3 -m inge6.main

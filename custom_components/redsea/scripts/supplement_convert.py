# -----------------------------------------------------------------------------
# !/usr/bin/python
# -----------------------------------------------------------------------------
import json

filename = "./supplements_list.json"

with open(filename) as f:
    supplement_bd = json.load(f)
    for supplement in supplement_bd:
        supplement["fullname"] = supplement["brand_name"] + " - " + supplement["name"]

print("SUPPLEMENTS=" + json.dumps(supplement_bd, indent=4))

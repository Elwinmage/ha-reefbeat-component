"""Check translation keys.

This script check the consistency of translation keys in code and tranlsation files

"""

from colorama import Fore, Style

import json
import os
import re
import sys

base_path = os.path.dirname(__file__)

print(base_path)

const_file: str = f"{base_path}/../const.py"

translations_path = f"{base_path}/../translations"

entity_domains: list[str] = []
keys_in_code: list[str] = []

with open(const_file) as f:
    entity_domains = list(
        map(
            lambda x: x.replace(r"Platform.", "").lower(),
            re.findall(r"Platform\.[A-Z\_]*", f.read()),
        )
    )
    entity_domains.sort()


langs = []

with open(f"{base_path}/../strings.json") as f:
    langs += [{"lang": "strings", "data": json.load(f), "translations_keys": []}]
for file in os.listdir(translations_path):
    if file.endswith(".json"):
        with open(translations_path + "/" + file) as f:
            langs += [
                {
                    "lang": file.replace(".json", ""),
                    "data": json.load(f),
                    "translations_keys": [],
                }
            ]

for entity_domain in entity_domains:
    # Get keys in code
    with open(f"{base_path}/../" + entity_domain + ".py") as f:
        keys_in_code += list(
            map(
                lambda x: entity_domain
                + "."
                + x.replace(r"translation_key=", "").replace('"', ""),
                re.findall(r"translation_key=\"[a-zA-Z0-9\-\_]*\"", f.read()),
            )
        )
    for lang in langs:
        lang_trans = list(
            map(
                lambda x: entity_domain + "." + x,
                lang["data"]["entity"][entity_domain].keys(),
            )
        )
        lang_trans.sort()
        lang["translations_keys"] += lang_trans

# Patch for RSLED auto_[1-7]
for cpt in range(1, 8):
    keys_in_code += ["sensor.auto_" + str(cpt)]
keys_in_code.sort()
keys_in_code.remove("sensor.auto_")
keys_in_code.remove("sensor.auto_")
## End of patch

modifs: int = 0

for lang in langs:
    path = "translations/"
    if lang["lang"] == "strings":
        path = ""
    no_more_needed = list(set(lang["translations_keys"]) - set(keys_in_code))
    needed = list(set(keys_in_code) - set(lang["translations_keys"]))

    if len(needed) > 0:
        modifs += len(needed)
        print(
            "["
            + str(len(needed))
            + "] Needed in "
            + Fore.CYAN
            + path
            + lang["lang"]
            + ".json"
        )
        for need in needed:
            print(Style.RESET_ALL + "  -> " + Fore.RED + need)

        print(Style.RESET_ALL)

    if len(no_more_needed) > 0:
        modifs += len(no_more_needed)
        print(
            "["
            + str(len(no_more_needed))
            + "] No More Needed in "
            + Fore.CYAN
            + path
            + lang["lang"]
            + ".json"
        )
        for nm_need in no_more_needed:
            print(Style.RESET_ALL + "  -> " + Fore.YELLOW + nm_need)

        print(Style.RESET_ALL)

if modifs > 0:
    print(Fore.RED + str(modifs) + Style.RESET_ALL + " modifications needed")
    sys.exit(1)
else:
    print("All " + Fore.GREEN + "good" + Style.RESET_ALL + ", no modifications needed")
    sys.exit(0)

import json
import os
import re

from colorama import Fore, Style

# Base path configuration - automatically set to custom_components/redsea directory
# Script location: ha-reefbeat-component/scripts/check_translation.py
# Target location: ha-reefbeat-component/custom_components/redsea/
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(script_dir)
base_path: str = os.path.join(repo_root, "custom_components", "redsea")

const_file: str = os.path.join(base_path, "const.py")
translations_path: str = os.path.join(base_path, "translations")
strings_file: str = os.path.join(base_path, "strings.json")

entity_domains: list[str] = []
keys_in_code: list[str] = []
# Dictionary to store options for each entity: {domain.key: [options]}
entity_options: dict[str, list[str]] = {}

with open(const_file) as f:
    entity_domains = list(
        map(
            lambda x: x.replace(r"Platform.", "").lower(),
            re.findall(r"Platform\.[A-Z\_]*", f.read()),
        )
    )
    entity_domains.sort()


langs = []

with open(strings_file) as f:
    langs += [
        {
            "lang": "strings",
            "data": json.load(f),
            "translations_keys": [],
            "state_keys": {},
        }
    ]
for file in os.listdir(translations_path):
    if file.endswith(".json"):
        with open(translations_path + "/" + file) as f:
            langs += [
                {
                    "lang": file.replace(".json", ""),
                    "data": json.load(f),
                    "translations_keys": [],
                    "state_keys": {},
                }
            ]

for entity_domain in entity_domains:
    # Get keys in code
    entity_file = os.path.join(base_path, f"{entity_domain}.py")
    with open(entity_file) as f:
        content = f.read()

        # Find all translation_key entries
        translation_keys = list(
            map(
                lambda x: entity_domain
                + "."
                + x.replace(r"translation_key=", "").replace('"', ""),
                re.findall(r"translation_key=\"[a-zA-Z0-9\-\_]*\"", content),
            )
        )
        keys_in_code += translation_keys

        # For each translation_key, try to find associated options
        # We need to split the file into entity description blocks
        # Pattern: look for blocks that contain both translation_key and options

        # Split by common patterns that indicate new entity descriptions
        # Look for EntityDescription( blocks
        blocks = re.split(
            r"\n\s*(?:ReefBeat|ReefLed|ReefWave|ReefDose|ReefATO|ReefMat|ReefRun)\w*(?:Sensor|Select)EntityDescription\(",
            content,
        )

        for block in blocks:
            # Find translation_key in this block
            trans_key_match = re.search(
                r"translation_key=\"([a-zA-Z0-9\-\_]*)\"", block
            )
            if trans_key_match:
                trans_key = trans_key_match.group(1)

                # Find options in the same block (must come after translation_key and before next entity)
                # Look for options=[ followed by content until ]
                options_match = re.search(r"options=\[(.*?)\]", block, re.DOTALL)

                if options_match:
                    options_str = options_match.group(1)
                    # Parse the options list - extract quoted strings
                    options = re.findall(r"\"([a-zA-Z0-9\-\_]+)\"", options_str)

                    # Also check for list() or constants like WAVE_TYPES
                    if not options:
                        # Check for things like list(HW_MAT_MODEL) or WAVE_TYPES
                        const_match = re.search(
                            r"options=\s*(?:list\()?([\w_]+)\)?", block
                        )
                        if const_match:
                            # For now, we'll note this but can't extract from constants
                            # unless we parse const.py as well
                            pass

                    if options:
                        full_key = f"{entity_domain}.{trans_key}"
                        entity_options[full_key] = options

    # Get translation keys from JSON files
    for lang in langs:
        entity_data = lang["data"]["entity"].get(entity_domain, {})

        for key, value in entity_data.items():
            lang_key = entity_domain + "." + key
            lang["translations_keys"].append(lang_key)

            # Check if this entity has state translations
            if isinstance(value, dict) and "state" in value:
                state_options = list(value["state"].keys())
                lang["state_keys"][lang_key] = state_options

# Patch for RSLED auto_[1-7]
for cpt in range(1, 8):
    keys_in_code += ["sensor.auto_" + str(cpt)]
keys_in_code.sort()
keys_in_code.remove("sensor.auto_")
keys_in_code.remove("sensor.auto_")
## End of patch

all_good: bool = True

for lang in langs:
    path = "translations/"
    if lang["lang"] == "strings":
        path = ""

    # Check entity keys (translation_key)
    no_more_needed = list(set(lang["translations_keys"]) - set(keys_in_code))
    needed = list(set(keys_in_code) - set(lang["translations_keys"]))

    if len(needed) > 0:
        all_good = False
        print(
            "["
            + str(len(needed))
            + "] Entity keys needed in "
            + Fore.CYAN
            + path
            + lang["lang"]
            + ".json"
        )
        for need in needed:
            print(Style.RESET_ALL + "  -> " + Fore.RED + need)

        print(Style.RESET_ALL)

    if len(no_more_needed) > 0:
        all_good = False
        print(
            "["
            + str(len(no_more_needed))
            + "] Entity keys no more needed in "
            + Fore.CYAN
            + path
            + lang["lang"]
            + ".json"
        )
        for nm_need in no_more_needed:
            print(Style.RESET_ALL + "  -> " + Fore.YELLOW + nm_need)

        print(Style.RESET_ALL)

    # Check state options for entities with options
    for entity_key, code_options in entity_options.items():
        # Get translated options for this entity
        translated_options = lang["state_keys"].get(entity_key, [])

        # Find missing and extra options
        missing_options = list(set(code_options) - set(translated_options))
        extra_options = list(set(translated_options) - set(code_options))

        if len(missing_options) > 0:
            all_good = False
            print(
                f"[{len(missing_options)}] State options needed for {Fore.CYAN}{entity_key}{Style.RESET_ALL} in {Fore.CYAN}{path}{lang['lang']}.json"
            )
            for option in sorted(missing_options):
                print(Style.RESET_ALL + "  -> " + Fore.RED + option)
            print(Style.RESET_ALL)

        if len(extra_options) > 0:
            all_good = False
            print(
                f"[{len(extra_options)}] State options no more needed for {Fore.CYAN}{entity_key}{Style.RESET_ALL} in {Fore.CYAN}{path}{lang['lang']}.json"
            )
            for option in sorted(extra_options):
                print(Style.RESET_ALL + "  -> " + Fore.YELLOW + option)
            print(Style.RESET_ALL)

if all_good:
    print("All " + Fore.GREEN + "good" + Style.RESET_ALL + ", no modifications needed")

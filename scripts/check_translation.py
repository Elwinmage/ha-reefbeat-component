import ast
import json
import os
import re
import sys

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


# -----------------------------------------------------------------------------
# AST-based extraction of translation_key values
# -----------------------------------------------------------------------------
#
# The naive regex `translation_key="literal"` misses valid patterns:
#   - variable indirection:  translation_key=my_var  (where my_var = "foo")
#   - dict lookup:           translation_key={"a": "foo"}.get(k, "bar")
#   - dict pool + variable:  tk = {...}.get(k, "d");  translation_key=tk
#   - if/elif branches:      per-branch string assignments to a common var
#
# All of these are valid Python that should not force contorted code just to
# satisfy the linter. This AST walker collects every string literal that could
# ever end up passed as `translation_key=` — following one level of variable
# indirection and inspecting dict literals in-place.


def _string_values_from_expr(node: ast.AST) -> set[str]:
    """Extract string constants that this expression could evaluate to.

    Handles:
      - ast.Constant                    -> {value} if str
      - ast.Dict                        -> {every str value in the dict}
      - ast.Call to .get on ast.Dict   -> dict values + default arg
    """
    result: set[str] = set()
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        result.add(node.value)
    elif isinstance(node, ast.Dict):
        for val in node.values:
            result |= _string_values_from_expr(val)
    elif (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
    ):
        # Extract values from the dict being called
        result |= _string_values_from_expr(node.func.value)
        # And from the default value (second positional arg)
        if len(node.args) >= 2:
            result |= _string_values_from_expr(node.args[1])
    return result


def _string_list_from_expr(
    node: ast.AST, list_pool: dict[str, list[str]]
) -> list[str] | None:
    """Extract a list of string constants from an `options=` expression.

    Handles:
      - ast.List([str, ...])
      - ast.Tuple((str, ...))
      - ast.Call: list(NAME) or tuple(NAME) where NAME is a known list/tuple
      - ast.Name: direct reference to a known list/tuple variable
    """
    if isinstance(node, (ast.List, ast.Tuple)):
        out: list[str] = []
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                out.append(elt.value)
        return out or None
    if isinstance(node, ast.Name):
        return list_pool.get(node.id)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in ("list", "tuple")
        and len(node.args) == 1
    ):
        return _string_list_from_expr(node.args[0], list_pool)
    return None


def _collect_string_pool(
    tree: ast.AST,
) -> tuple[dict[str, set[str]], dict[str, list[str]]]:
    """Return (str_pool, list_pool) computed from module-level assignments.

    * str_pool  maps a variable name to every string literal it might hold
    * list_pool maps a variable name to a list of strings if it's assigned a
      list/tuple of string constants (useful for `options=list(FOO_TUPLE)`)

    Both plain `x = ...` and annotated `x: T = ...` assignments are handled.
    """
    str_pool: dict[str, set[str]] = {}
    list_pool: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        # Normalize both Assign (`x = ...`) and AnnAssign (`x: T = ...`) to
        # a list of (target, value) pairs.
        pairs: list[tuple[ast.expr, ast.expr]] = []
        if isinstance(node, ast.Assign):
            for target in node.targets:
                pairs.append((target, node.value))
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            pairs.append((node.target, node.value))
        else:
            continue

        for target, value in pairs:
            if not isinstance(target, ast.Name):
                continue
            values = _string_values_from_expr(value)
            if values:
                str_pool.setdefault(target.id, set()).update(values)
            if isinstance(value, (ast.List, ast.Tuple)):
                strs = [
                    e.value
                    for e in value.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)
                ]
                if strs:
                    list_pool[target.id] = strs
    return str_pool, list_pool


def _extract_translation_keys(content: str) -> tuple[list[str], dict[str, list[str]]]:
    """Return (translation_keys, options_per_key) for a module.

    `translation_keys` is the flat list of every string that appears as the
    value of a `translation_key=` keyword argument (possibly via indirection).

    `options_per_key` maps `<translation_key>` -> list of option strings when
    a description bundle also provides `options=[...]`. This mirrors the
    previous regex-based behavior for enum state validation.
    """
    tree = ast.parse(content)
    str_pool, list_pool = _collect_string_pool(tree)

    keys: list[str] = []
    options: dict[str, list[str]] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # Find the translation_key= and options= keyword args on this Call.
        tk_values: set[str] = set()
        opt_strings: list[str] | None = None
        for kw in node.keywords:
            if kw.arg == "translation_key":
                if isinstance(kw.value, ast.Name):
                    tk_values |= str_pool.get(kw.value.id, set())
                else:
                    tk_values |= _string_values_from_expr(kw.value)
            elif kw.arg == "options":
                opt_strings = _string_list_from_expr(kw.value, list_pool)

        for tk in tk_values:
            keys.append(tk)
            if opt_strings:
                options[tk] = opt_strings

    return keys, options


for entity_domain in entity_domains:
    # Get keys in code
    entity_file = os.path.join(base_path, f"{entity_domain}.py")
    with open(entity_file) as f:
        content = f.read()

        # AST-based extraction — see helpers above. This is aware of variable
        # indirection and dict lookups, so patterns like
        #     tk = {"ph": "probe_ph_value", ...}.get(ptype, "probe_value")
        #     ReefBeatSensorEntityDescription(translation_key=tk, ...)
        # are correctly detected without forcing per-branch literal spelling.
        module_keys, module_options = _extract_translation_keys(content)
        keys_in_code += [f"{entity_domain}.{k}" for k in module_keys]
        for tk, opts in module_options.items():
            entity_options[f"{entity_domain}.{tk}"] = opts

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

# RSLED sensor.auto_[1-7] are built with a runtime string concat:
#   translation_key="auto_" + str(auto_id)
# The AST walker can't statically evaluate the concatenation and therefore
# does not emit any partial "auto_" key. We add the real 7 keys explicitly.
for cpt in range(1, 8):
    keys_in_code += ["sensor.auto_" + str(cpt)]
keys_in_code.sort()
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
else:
    sys.exit(1)

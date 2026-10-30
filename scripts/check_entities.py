#!/usr/bin/env python3
"""
check_entities.py
=================
Vérifie que toutes les entités HA déclarées dans les intégrations supportées
(ha-reefbeat-component, ha-aquamedic-component) sont bien référencées dans la
custom card ha-reef-card.

Étape 1 : Extraction AST des translation_keys par device et plateforme
          (un extracteur par intégration, voir INTEGRATIONS)
Étape 2 : Extraction des entity keys référencées dans les fichiers TS de la card
Étape 3 : Rapport de couverture (présent / manquant)
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# Script lives in ha-reef-card/scripts/
# ha-reef-card/           = SCRIPT_DIR.parent
# ha-reefbeat-component/  = SCRIPT_DIR.parent.parent / "ha-reefbeat-component"
SCRIPT_DIR = Path(__file__).resolve().parent
CARD_ROOT = SCRIPT_DIR.parent  # ha-reef-card/
CARD_DIR = CARD_ROOT / "src"  # ha-reef-card/src/
COMPONENT_ROOT = CARD_ROOT.parent / "ha-reefbeat-component"  # ../ha-reefbeat-component/
COMPONENT_DIR = COMPONENT_ROOT / "custom_components" / "redsea"

COMPONENT_GIT_URL = "https://github.com/Elwinmage/ha-reefbeat-component"

# ha-aquamedic-component/ = SCRIPT_DIR.parent.parent / "ha-aquamedic-component"
AQUAMEDIC_ROOT = CARD_ROOT.parent / "ha-aquamedic-component"
AQUAMEDIC_DIR = AQUAMEDIC_ROOT / "custom_components" / "aquamedic"
AQUAMEDIC_GIT_URL = "https://github.com/Elwinmage/ha-aquamedic-component"

# ---------------------------------------------------------------------------
# Coordinator → device mapping
# (from coordinator.py class hierarchy + auto_detect/config_flow context)
# ---------------------------------------------------------------------------
# Maps coordinator class names to canonical device short-names
COORDINATOR_TO_DEVICE: dict[str, list[str]] = {
    "ReefLedCoordinator": ["rsled_g1"],
    "ReefLedG2Coordinator": ["rsled_g2"],
    "ReefVirtualLedCoordinator": ["rsled_virtual"],
    "ReefMatCoordinator": ["rsmat"],
    "ReefDoseCoordinator": ["rsdose"],
    "ReefATOCoordinator": ["rsato"],
    "ReefPowerCoordinator": ["rspower"],
    "ReefControlCoordinator": ["rscontrol"],
    "ReefRunCoordinator": ["rsrun"],
    "ReefWaveCoordinator": ["rswave"],
    # Cloud coordinator — no card device
    "ReefBeatCloudCoordinator": ["_cloud"],
    # Base / protocol guards used in isinstance() conditions
    "_CloudLinkedCoordinator": [
        "rsled_g1",
        "rsled_g2",
        "rsled_virtual",
        "rsmat",
        "rspower",
        "rcontrol",
        "rsdose",
        "rsato",
        "rsrun",
        "rswave",
    ],
    "ReefBeatCloudLinkedCoordinator": [
        "rsled_g1",
        "rsled_g2",
        "rsled_virtual",
        "rsmat",
        "rspower",
        "rscontrol",
        "rsdose",
        "rsato",
        "rsrun",
        "rswave",
    ],
}

# Platforms we parse
PLATFORMS = [
    "switch",
    "sensor",
    "number",
    "select",
    "binary_sensor",
    "button",
    "light",
    "text",
    "time",
    "update",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def flatten_isinstance_args(node: ast.expr) -> list[str]:
    """Return all class names from isinstance(x, Cls) or isinstance(x, (A, B, C))."""
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Tuple):
        names = []
        for elt in node.elts:
            if isinstance(elt, ast.Name):
                names.append(elt.id)
        return names
    return []


def get_translation_key(node: ast.expr | None) -> str | None:
    """Extract translation_key='...' from a keyword arg or from a Call node."""
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def extract_translation_keys_from_call(call: ast.Call) -> str | None:
    """From a Description(... translation_key='foo' ...) call, extract translation_key."""
    for kw in call.keywords:
        if kw.arg == "translation_key":
            return get_translation_key(kw.value)
    return None


def extract_translation_keys_from_collection(node: ast.expr) -> list[str]:
    """
    Given a tuple/list of description objects, extract all translation_key values.
    Handles:
      - Tuple/List of Call nodes (static lists like COMMON_SWITCHES)
      - A single Call node
    """
    keys: list[str] = []
    if isinstance(node, (ast.Tuple, ast.List)):
        for elt in node.elts:
            if isinstance(elt, ast.Call):
                tk = extract_translation_keys_from_call(elt)
                if tk:
                    keys.append(tk)
    elif isinstance(node, ast.Call):
        tk = extract_translation_keys_from_call(node)
        if tk:
            keys.append(tk)
    return keys


# ---------------------------------------------------------------------------
# Step 1 – AST extraction of component entities
# ---------------------------------------------------------------------------


class EntityExtractor(ast.NodeVisitor):
    """
    Walks a platform file and builds:
        { device_short_name -> { platform -> [translation_key, ...] } }

    Strategy:
    1. Collect all module-level var assignments of Description tuples/lists.
    2. Walk async_setup_entry body statement by statement.
       - Independent `if` blocks each carry their own guard (NOT accumulated).
       - `if/elif/else` chains share consumed context.
    3. When entities.extend() / entities.append() / _add_described_entities() is
       found, collect translation_keys from the iterated list (static var lookup
       or inline Description calls) and record them for active devices.
    """

    # All real device names we care about
    ALL_DEVICES: list[str] = [
        "rsled_g1",
        "rsled_g2",
        "rsled_virtual",
        "rsmat",
        "rsdose",
        "rsato",
        "rsrun",
        "rswave",
        "rspower",
        "rscontrol",
    ]

    def __init__(self, platform: str) -> None:
        self.platform = platform
        # { var_name -> [translation_key, ...] }
        self.static_descs: dict[str, list[str]] = {}
        # result: device -> platform -> [translation_key]
        self.result: dict[str, dict[str, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )

    # ------------------------------------------------------------------ #
    # Pass 1 – collect static description lists from module level         #
    # ------------------------------------------------------------------ #

    def visit_Module(self, node: ast.Module) -> None:
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                self._collect_static(stmt)
            elif isinstance(stmt, ast.AnnAssign):
                # e.g. COMMON_SWITCHES: tuple[...] = (...)
                if isinstance(stmt.target, ast.Name) and stmt.value is not None:
                    keys = extract_translation_keys_from_collection(stmt.value)
                    if keys:
                        self.static_descs[stmt.target.id] = keys
        self.generic_visit(node)

    def _collect_static(self, node: ast.Assign) -> None:
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            keys = extract_translation_keys_from_collection(node.value)
            if keys:
                self.static_descs[target.id] = keys

    # ------------------------------------------------------------------ #
    # Pass 2 – walk async_setup_entry                                     #
    # ------------------------------------------------------------------ #

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if node.name == "async_setup_entry":
            self._walk_stmts(node.body, active_devices=set(self.ALL_DEVICES))

    # ---- Core recursive walker ----

    def _walk_stmts(self, stmts: list[ast.stmt], active_devices: set[str]) -> None:
        """
        Walk a list of statements.  `active_devices` is the set of devices that
        could be active at this point in the code.

        Independent `if` blocks are handled by computing their own guard
        *relative to* active_devices — NOT relative to siblings.
        if/elif chains are handled with consumed tracking.
        """
        i = 0
        while i < len(stmts):
            stmt = stmts[i]
            if isinstance(stmt, ast.If):
                self._walk_if_chain(stmt, active_devices)
            else:
                self._walk_single_stmt(stmt, active_devices)
            i += 1

    def _walk_if_chain(self, node: ast.If, active_devices: set[str]) -> None:
        """
        Walk an if / elif* / else? chain.
        consumed tracks which coordinator classes have already matched
        (so elif branches implicitly exclude them).
        """
        consumed_classes: list[str] = []

        current: ast.If | None = node
        while current is not None:
            pos_cls, neg_cls = self._parse_test(current.test)

            # Restrict active to those matching this branch's guard
            branch_devices = self._apply_guard(
                active_devices, pos_cls, neg_cls + consumed_classes
            )
            self._walk_stmts(current.body, branch_devices)
            consumed_classes.extend(pos_cls)

            # Descend into else/elif
            if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
                current = current.orelse[0]
            else:
                if current.orelse:  # plain else
                    else_devices = self._apply_guard(
                        active_devices, [], consumed_classes
                    )
                    self._walk_stmts(current.orelse, else_devices)
                break

    # ---- Guard logic ----

    def _parse_test(self, test: ast.expr) -> tuple[list[str], list[str]]:
        """Return (positive_classes, negative_classes) from isinstance guards."""
        pos: list[str] = []
        neg: list[str] = []
        self._collect_isinstance(test, pos, neg, negated=False)
        return pos, neg

    def _collect_isinstance(
        self,
        node: ast.expr,
        pos: list[str],
        neg: list[str],
        negated: bool,
    ) -> None:
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            for v in node.values:
                self._collect_isinstance(v, pos, neg, negated)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            self._collect_isinstance(node.operand, pos, neg, not negated)
        elif isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Name)
                and func.id == "isinstance"
                and len(node.args) >= 2
            ):
                classes = flatten_isinstance_args(node.args[1])
                (neg if negated else pos).extend(classes)

    def _apply_guard(
        self,
        active: set[str],
        pos_classes: list[str],
        neg_classes: list[str],
    ) -> set[str]:
        """
        Given a set of currently active devices, apply isinstance() filters.

        - pos_classes: device must be one of these coordinator types
        - neg_classes: device must NOT be any of these coordinator types
        """

        def resolve(classes: list[str]) -> set[str]:
            devs: set[str] = set()
            for cls in classes:
                devs.update(COORDINATOR_TO_DEVICE.get(cls, []))
            return devs

        result = set(active)

        if pos_classes:
            allowed = resolve(pos_classes)
            result &= allowed

        if neg_classes:
            excluded = resolve(neg_classes)
            result -= excluded

        return result

    # ---- Call handlers ----

    def _handle_call(self, call: ast.Call, active_devices: set[str]) -> None:
        """Dispatch entities.extend / entities.append / _add_described_entities."""
        if not isinstance(call.func, ast.Attribute):
            return
        attr = call.func.attr

        if attr == "extend" and call.args:
            arg = call.args[0]
            if isinstance(arg, ast.GeneratorExp):
                keys = self._keys_from_generator(arg)
            elif isinstance(arg, (ast.List, ast.Tuple)):
                keys = self._keys_from_collection(arg)
            else:
                keys = []
            for k in keys:
                self._record(k, active_devices)

        elif attr == "append" and call.args:
            arg = call.args[0]
            tk = self._tk_from_entity_ctor(arg)
            if tk:
                self._record(tk, active_devices)

        # _add_described_entities(entities, device, EntityClass, DESCRIPTIONS)
        # The 4th positional arg is the descriptions list/variable
        elif attr == "extend" or (
            isinstance(call.func, ast.Name)
            and call.func.id == "_add_described_entities"  # type: ignore[union-attr]
        ):
            pass  # handled above

    # Also handle _add_described_entities called as a plain function
    def _handle_expr_call(self, call: ast.Call, active_devices: set[str]) -> None:
        """Handle _add_described_entities(entities, device, EntityClass, DESCRIPTIONS)."""
        func = call.func
        if isinstance(func, ast.Name) and func.id == "_add_described_entities":
            if len(call.args) >= 4:
                keys = self._keys_from_name_or_collection(call.args[3])
                for k in keys:
                    self._record(k, active_devices)

    def _walk_single_stmt(self, stmt: ast.stmt, active_devices: set[str]) -> None:
        """Handle a single non-if statement."""
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            self._handle_call(call, active_devices)
            self._handle_expr_call(call, active_devices)
        elif isinstance(stmt, ast.For):
            self._walk_stmts(stmt.body, active_devices)
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    keys = extract_translation_keys_from_collection(stmt.value)
                    if keys:
                        self.static_descs[target.id] = keys
        elif isinstance(stmt, ast.AnnAssign):
            # `descs: list[...] = [...]`
            if isinstance(stmt.target, ast.Name) and stmt.value is not None:
                keys = extract_translation_keys_from_collection(stmt.value)
                if keys:
                    self.static_descs[stmt.target.id] = keys

    # ---- Key extraction helpers ----

    def _keys_from_generator(self, gen: ast.GeneratorExp) -> list[str]:
        keys: list[str] = []
        for comp in gen.generators:
            keys.extend(self._keys_from_name_or_collection(comp.iter))
        return keys

    def _keys_from_name_or_collection(self, node: ast.expr) -> list[str]:
        if isinstance(node, ast.Name):
            return list(self.static_descs.get(node.id, []))
        if isinstance(node, (ast.Tuple, ast.List)):
            return self._keys_from_collection(node)
        if isinstance(node, ast.Call):
            # tuple(ds) or list(ds)
            func = node.func
            if (
                isinstance(func, ast.Name)
                and func.id in ("tuple", "list")
                and node.args
            ):
                return self._keys_from_name_or_collection(node.args[0])
        return []

    def _keys_from_collection(self, node: ast.expr) -> list[str]:
        keys: list[str] = []
        if isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                if isinstance(elt, ast.Call):
                    tk = extract_translation_keys_from_call(elt)
                    if tk:
                        keys.append(tk)
        return keys

    def _tk_from_entity_ctor(self, node: ast.expr) -> str | None:
        if not isinstance(node, ast.Call):
            return None
        # Direct: DescriptionClass(... translation_key='foo' ...)
        tk = extract_translation_keys_from_call(node)
        if tk:
            return tk
        # Nested: EntityClass(device, DescriptionClass(...))
        if len(node.args) >= 2 and isinstance(node.args[1], ast.Call):
            return extract_translation_keys_from_call(node.args[1])
        return None

    # ---- Record ----

    def _record(self, translation_key: str, devices: set[str]) -> None:
        for dev in devices:
            if dev == "_cloud":
                continue
            lst = self.result[dev][self.platform]
            if translation_key not in lst:
                lst.append(translation_key)


def extract_component_entities(component_dir: Path) -> dict[str, dict[str, list[str]]]:
    """
    Returns: { device: { platform: [translation_key, ...] } }
    """
    result: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    for platform in PLATFORMS:
        py_file = component_dir / f"{platform}.py"
        if not py_file.exists():
            continue

        src = py_file.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(py_file))

        extractor = EntityExtractor(platform)
        extractor.visit(tree)

        # Merge
        for dev, platforms in extractor.result.items():
            for plat, keys in platforms.items():
                for k in keys:
                    if k not in result[dev][plat]:
                        result[dev][plat].append(k)

    # Poseidon entities: built from classes, not descriptions (see below)
    for dev, platforms in extract_poseidon_entities(component_dir).items():
        for plat, keys in platforms.items():
            for k in keys:
                if k not in result[dev][plat]:
                    result[dev][plat].append(k)

    return dict(result)


# ---------------------------------------------------------------------------
# Step 1 – Poseidon entities of the Red Sea component
# ---------------------------------------------------------------------------
#
# The Poseidon entry adds entities to every device whose keys are known
# (mode switch, polling pause, strategy). They belong to the Poseidon config
# entry but are attached to the device, so the card sees them as the
# device's own. They are not described by EntityDescription tuples: each one
# is a class with an ``_attr_translation_key``, created by an adder callback
# in the platform's async_setup_entry, which the EntityExtractor walk cannot
# follow. The platform of a class is the platform file importing it.

POSEIDON_MODULE = "poseidon.switch_entity"

# Card devices a Poseidon entity can show on: every real Red Sea device.
# A LED group is no device of its own, it has no keys.
POSEIDON_DEVICES: list[str] = [
    d for d in EntityExtractor.ALL_DEVICES if d != "rsled_virtual"
]


def _class_translation_keys(tree: ast.Module) -> dict[str, str]:
    """{ class name: its _attr_translation_key } of a module."""
    keys: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            target: ast.expr | None = None
            value: ast.expr | None = None
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                target, value = stmt.targets[0], stmt.value
            elif isinstance(stmt, ast.AnnAssign):
                target, value = stmt.target, stmt.value
            if (
                isinstance(target, ast.Name)
                and target.id == "_attr_translation_key"
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                keys[node.name] = value.value
    return keys


def extract_poseidon_entities(
    component_dir: Path,
) -> dict[str, dict[str, list[str]]]:
    """
    Returns: { device: { platform: [translation_key, ...] } } for the
    Poseidon entities, or {} with a component without Poseidon.
    """
    module_file = component_dir / (POSEIDON_MODULE.replace(".", "/") + ".py")
    if not module_file.exists():
        return {}
    class_keys = _class_translation_keys(
        ast.parse(module_file.read_text(encoding="utf-8"), filename=str(module_file))
    )

    per_platform: dict[str, list[str]] = defaultdict(list)
    for platform in PLATFORMS:
        py_file = component_dir / f"{platform}.py"
        if not py_file.exists():
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.ImportFrom)
                and (node.module or "").endswith(POSEIDON_MODULE)
            ):
                continue
            for alias in node.names:
                key = class_keys.get(alias.name)
                if key and key not in per_platform[platform]:
                    per_platform[platform].append(key)

    result: dict[str, dict[str, list[str]]] = {}
    for device in POSEIDON_DEVICES:
        result[device] = {plat: list(keys) for plat, keys in per_platform.items()}
    return result


# ---------------------------------------------------------------------------
# Step 1 bis – AST extraction of the Aqua Medic component entities
# ---------------------------------------------------------------------------
#
# ha-aquamedic-component has a single coordinator for the whole account, so
# its platforms do not guard on a coordinator class like the Red Sea ones do:
# they compare the Gizwits product key of each device. The walk below follows
# those comparisons instead of isinstance() calls.

# Firmware variants, as the platforms tell them apart (product key constants
# of const.py). DC_SKIMMER_PRODUCT_KEY is an alias of the DC Runner series key.
AQUAMEDIC_PRODUCT_KEYS: dict[str, str] = {
    "SMARTDRIFT_PRODUCT_KEY": "smartdrift",
    "DC_RUNNER_SERIES_PRODUCT_KEY": "runner_series",
    "DC_SKIMMER_PRODUCT_KEY": "runner_series",
    "DC_RUNNER_PRODUCT_KEY": "runner_legacy",
}

AQUAMEDIC_VARIANTS: frozenset[str] = frozenset(AQUAMEDIC_PRODUCT_KEYS.values())

# Firmware variant → card devices showing it. Both DC Runner firmwares serve
# the return pump and the skimmer: the role comes from the user (pump_role
# select), not from the product key, so each view must cover both.
AQUAMEDIC_VARIANT_DEVICES: dict[str, list[str]] = {
    "smartdrift": ["smartdrift"],
    "runner_series": ["dcrunner", "dcskimmer"],
    "runner_legacy": ["dcrunner", "dcskimmer"],
}

# Helper predicates of the component, called with a product key, and the
# variants for which they are true (resp. return something other than None).
AQUAMEDIC_GUARD_FUNCTIONS: dict[str, frozenset[str]] = {
    # maintenance.py: the role of these pumps cannot be read from the API
    "role_is_user_defined": frozenset({"runner_series", "runner_legacy"}),
    # schedule.py: products having a time-slot scheduler
    "layout_for": frozenset({"smartdrift", "runner_series"}),
}

AQUAMEDIC_DEVICES: list[str] = ["smartdrift", "dcrunner", "dcskimmer"]


class AquaMedicEntityExtractor:
    """
    Walks one platform file of ha-aquamedic-component and builds:
        { firmware_variant -> [translation_key, ...] }

    Strategy:
    1. Collect the module-level Description tuples (and single Descriptions),
       and the `_attr_translation_key` of the entity classes that have no
       description (e.g. the pump role select).
    2. Walk the `for did, dev in coordinator.data.items()` loop of
       async_setup_entry, following the product key tests:
         - if / elif / else chains, each branch with its own variants;
         - `if <test>: continue`, which restricts the rest of the loop;
         - `descs = SOME_DESCRIPTIONS`, resolved when `descs` is iterated.
    3. Record the translation keys of every entities.append() for the variants
       active at that point.

    Entities whose translation key is computed at run time (the maintenance
    tasks) are deliberately not collected: the maintenance view picks them up
    from their `reef_role` attribute, not from a mapping.
    """

    def __init__(self) -> None:
        # { var_name -> [translation_key, ...] }
        self.static_descs: dict[str, list[str]] = {}
        # { class_name -> translation_key } from `_attr_translation_key = "..."`
        self.class_keys: dict[str, str] = {}
        # { var_name -> [(keys, variants)] } for `descs = X` made under a guard
        self.aliases: dict[str, list[tuple[list[str], set[str]]]] = {}
        # { var_name -> variants } for `x = guard_function(...)`
        self.guard_vars: dict[str, frozenset[str]] = {}
        # result: variant -> [translation_key]
        self.result: dict[str, list[str]] = defaultdict(list)

    # ---- Pass 1 ----

    def visit(self, tree: ast.Module) -> None:
        for stmt in tree.body:
            if isinstance(stmt, (ast.Assign, ast.AnnAssign)) and stmt.value is not None:
                targets = (
                    stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
                )
                keys = extract_translation_keys_from_collection(stmt.value)
                for target in targets:
                    if keys and isinstance(target, ast.Name):
                        self.static_descs[target.id] = keys
            elif isinstance(stmt, ast.ClassDef):
                for item in stmt.body:
                    if (
                        isinstance(item, ast.Assign)
                        and isinstance(item.value, ast.Constant)
                        and isinstance(item.value.value, str)
                        and any(
                            isinstance(t, ast.Name) and t.id == "_attr_translation_key"
                            for t in item.targets
                        )
                    ):
                        self.class_keys[stmt.name] = item.value.value
        for stmt in tree.body:
            if (
                isinstance(stmt, ast.AsyncFunctionDef)
                and stmt.name == "async_setup_entry"
            ):
                self._walk(stmt.body, set(AQUAMEDIC_VARIANTS))

    # ---- Guards ----

    def _variants_of(self, node: ast.expr) -> set[str]:
        """Variants named by a product key constant, or a tuple of them."""
        if isinstance(node, ast.Name):
            variant = AQUAMEDIC_PRODUCT_KEYS.get(node.id)
            return {variant} if variant else set()
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            found: set[str] = set()
            for elt in node.elts:
                found |= self._variants_of(elt)
            return found
        return set()

    def _eval(self, test: ast.expr, active: set[str]) -> set[str] | None:
        """
        Variants of `active` for which `test` is true.
        Returns None when the test says nothing about the product key.
        """
        if isinstance(test, ast.BoolOp):
            parts = [self._eval(v, active) for v in test.values]
            known = [p for p in parts if p is not None]
            if not known:
                return None
            if isinstance(test.op, ast.And):
                result = set(active)
                for part in known:
                    result &= part
                return result
            # `or` with an unknown operand may be true for any variant
            if len(known) != len(parts):
                return None
            result = set()
            for part in known:
                result |= part
            return result
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            inner = self._eval(test.operand, active)
            return None if inner is None else active - inner
        if isinstance(test, ast.Call):
            name = test.func.id if isinstance(test.func, ast.Name) else None
            if name in AQUAMEDIC_GUARD_FUNCTIONS:
                return active & AQUAMEDIC_GUARD_FUNCTIONS[name]
            return None
        if isinstance(test, ast.Compare) and len(test.ops) == 1:
            op, right = test.ops[0], test.comparators[0]
            # `layout is None` / `layout is not None`, layout = guard_function()
            if (
                isinstance(op, (ast.Is, ast.IsNot))
                and isinstance(test.left, ast.Name)
                and test.left.id in self.guard_vars
                and isinstance(right, ast.Constant)
                and right.value is None
            ):
                truthy = active & self.guard_vars[test.left.id]
                return active - truthy if isinstance(op, ast.Is) else truthy
            named = self._variants_of(right)
            if not named:
                return None
            if isinstance(op, (ast.Eq, ast.In)):
                return active & named
            if isinstance(op, (ast.NotEq, ast.NotIn)):
                return active - named
        return None

    # ---- Walk ----

    @staticmethod
    def _only_continues(body: list[ast.stmt]) -> bool:
        return all(isinstance(stmt, ast.Continue) for stmt in body)

    def _walk(self, stmts: list[ast.stmt], active: set[str]) -> None:
        active = set(active)
        for stmt in stmts:
            if isinstance(stmt, ast.If):
                # `if <test>: continue` narrows everything that follows
                if self._only_continues(stmt.body) and not stmt.orelse:
                    skipped = self._eval(stmt.test, active)
                    if skipped is not None:
                        active -= skipped
                    continue
                self._walk_if_chain(stmt, active)
            elif isinstance(stmt, ast.For):
                self._walk_for(stmt, active)
            elif (
                isinstance(stmt, (ast.Assign, ast.AnnAssign)) and stmt.value is not None
            ):
                targets = (
                    stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
                )
                for target in targets:
                    if isinstance(target, ast.Name):
                        self._assign(target.id, stmt.value, active)
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                self._handle_call(stmt.value, active, loop_keys=None)

    def _walk_if_chain(self, node: ast.If, active: set[str]) -> None:
        remaining = set(active)
        current: ast.If | None = node
        while current is not None:
            matched = self._eval(current.test, remaining)
            branch = remaining if matched is None else matched
            self._walk(current.body, branch)
            if matched is not None:
                remaining = remaining - matched
            if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
                current = current.orelse[0]
            else:
                if current.orelse:
                    self._walk(current.orelse, remaining)
                break

    def _assign(self, name: str, value: ast.expr, active: set[str]) -> None:
        # layout = layout_for(dev.product_key)
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id in AQUAMEDIC_GUARD_FUNCTIONS
        ):
            self.guard_vars[name] = AQUAMEDIC_GUARD_FUNCTIONS[value.func.id]
            return
        # descs = SWITCH_DESCRIPTIONS / descs = ()
        keys = self._keys_of(value)
        if keys is not None:
            self.aliases.setdefault(name, []).append((keys, set(active)))

    def _keys_of(self, node: ast.expr) -> list[str] | None:
        """Translation keys of a descriptions expression, None when unknown."""
        if isinstance(node, ast.Name):
            return self.static_descs.get(node.id)
        if isinstance(node, (ast.Tuple, ast.List)):
            return extract_translation_keys_from_collection(node)
        return None

    def _walk_for(self, node: ast.For, active: set[str]) -> None:
        # for desc in descs: / for desc in SWITCH_DESCRIPTIONS:
        loop_keys: list[tuple[list[str], set[str]]] | None = None
        if isinstance(node.iter, ast.Name):
            if node.iter.id in self.aliases:
                loop_keys = [
                    (keys, variants & active)
                    for keys, variants in self.aliases[node.iter.id]
                ]
            elif node.iter.id in self.static_descs:
                loop_keys = [(self.static_descs[node.iter.id], set(active))]
        if loop_keys is None:
            # The device loop itself, or a loop over run-time data
            self._walk(node.body, active)
            return
        for stmt in node.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                self._handle_call(stmt.value, active, loop_keys)
            elif isinstance(stmt, ast.If):
                # if desc.kind is LOCAL: append(A(...)) else: append(B(...))
                for branch in (stmt.body, stmt.orelse):
                    for inner in branch:
                        if isinstance(inner, ast.Expr) and isinstance(
                            inner.value, ast.Call
                        ):
                            self._handle_call(inner.value, active, loop_keys)

    def _handle_call(
        self,
        call: ast.Call,
        active: set[str],
        loop_keys: list[tuple[list[str], set[str]]] | None,
    ) -> None:
        if not (
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "append"
            and call.args
        ):
            return
        ctor = call.args[0]
        if not isinstance(ctor, ast.Call):
            return
        # Entity class carrying its own translation key
        cls = ctor.func.id if isinstance(ctor.func, ast.Name) else None
        if cls in self.class_keys:
            self._record([self.class_keys[cls]], active)
            return
        # Entity(coordinator, did, SOME_DESCRIPTION [, ...])
        for arg in ctor.args:
            if isinstance(arg, ast.Name) and arg.id in self.static_descs:
                self._record(self.static_descs[arg.id], active)
                return
        # Entity(coordinator, did, desc) inside `for desc in descs`
        if loop_keys is not None:
            for keys, variants in loop_keys:
                self._record(keys, variants)

    def _record(self, keys: list[str], variants: set[str]) -> None:
        for variant in variants:
            for key in keys:
                if key not in self.result[variant]:
                    self.result[variant].append(key)


def extract_aquamedic_entities(component_dir: Path) -> dict[str, dict[str, list[str]]]:
    """
    Returns: { card_device: { platform: [translation_key, ...] } }
    """
    result: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    for platform in PLATFORMS:
        py_file = component_dir / f"{platform}.py"
        if not py_file.exists():
            continue

        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        extractor = AquaMedicEntityExtractor()
        extractor.visit(tree)

        for variant, keys in extractor.result.items():
            for device in AQUAMEDIC_VARIANT_DEVICES[variant]:
                for k in keys:
                    if k not in result[device][platform]:
                        result[device][platform].append(k)

    return {dev: dict(platforms) for dev, platforms in result.items()}


# ---------------------------------------------------------------------------
# Integrations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Integration:
    """A Home Assistant integration whose entities the card must reference."""

    name: str  # hass domain
    label: str  # repository name, for messages
    root: Path  # local checkout, next to ha-reef-card
    component_dir: Path  # custom_components/<domain> inside it
    git_url: str  # cloned from there when the checkout is missing
    devices: tuple[str, ...]  # card devices it provides
    extract: Callable[[Path], dict[str, dict[str, list[str]]]]


INTEGRATIONS: list[Integration] = [
    Integration(
        name="redsea",
        label="ha-reefbeat-component",
        root=COMPONENT_ROOT,
        component_dir=COMPONENT_DIR,
        git_url=COMPONENT_GIT_URL,
        devices=tuple(EntityExtractor.ALL_DEVICES),
        extract=extract_component_entities,
    ),
    Integration(
        name="aquamedic",
        label="ha-aquamedic-component",
        root=AQUAMEDIC_ROOT,
        component_dir=AQUAMEDIC_DIR,
        git_url=AQUAMEDIC_GIT_URL,
        devices=tuple(AQUAMEDIC_DEVICES),
        extract=extract_aquamedic_entities,
    ),
]


def extract_all_component_entities(
    integrations: list[Integration],
) -> dict[str, dict[str, list[str]]]:
    """Merge the entities of every integration: { device: { platform: [key] } }."""
    result: dict[str, dict[str, list[str]]] = {}
    for integration in integrations:
        result.update(integration.extract(integration.component_dir))
    return result


# ---------------------------------------------------------------------------
# Step 2 – Extract entity keys from the card's TypeScript files
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Patterns to find entity references in card TypeScript files
# ---------------------------------------------------------------------------

# A card reference may carry an explicit HA domain prefix ("sensor.water_level")
# when two entities of the same device share one translation key and the mapping
# has to pick one of them. Only the translation key is captured: the component
# side is indexed by key, not by entity_id.
_DOMAIN = r"(?:[a-z_]+\.)?"

CARD_ENTITY_PATTERNS: list[re.Pattern[str]] = [
    # {"entity": "key"} or {entity: "key"} (with or without quotes around the key)
    re.compile(
        r'["\']?entity["\']?\s*:\s*["\']' + _DOMAIN + r'([a-z_][a-z0-9_]*)["\']'
    ),
    # entities['key'] or entities["key"]
    re.compile(r"entities\[['\"]" + _DOMAIN + r"([ a-z_][a-z0-9_]*)['\"]"),
    # "name": "snake_case_key"  — element key names in mapping objects
    re.compile(r'["\']?name["\']?\s*:\s*["\']' + _DOMAIN + r'([a-z_][a-z0-9_]+)["\']'),
    # "entity_id": "key"
    re.compile(
        r'["\']?entity_id["\']?\s*:\s*["\']' + _DOMAIN + r'([a-z_][a-z0-9_]*)["\']'
    ),
    # "target": "key"  — progress-bar / progress-circle / *-target elements
    re.compile(
        r'["\']?target["\']?\s*:\s*["\']' + _DOMAIN + r'([a-z_][a-z0-9_]*)["\']'
    ),
    # "value_entity": "key"  — overlay entity of a water-level element, which
    # displays one entity and reads its level from another
    re.compile(
        r'["\']?value_entity["\']?\s*:\s*["\']' + _DOMAIN + r'([a-z_][a-z0-9_]*)["\']'
    ),
    # ${entity.key.state} — inline template expressions
    re.compile(r"\$\{entity\.([a-z_][a-z0-9_]*)"),
    # _pressButton("key") — indirect callService via entity translation_key
    re.compile(r'_pressButton\([\'"]([a-z_][a-z0-9_]*)[\'"]'),
    # callService(..., { entity_id: ... }) patterns already covered above
    # but also: this.device.entities["key"] or this.device?.entities?.["key"]
    re.compile(r'\.entities\??\.\[?[\'"]([a-z_][a-z0-9_]*)[\'"]'),
]

# get_entity('key') is only a reliable display reference when called from mapping
# or dialog files.  In plain device logic files (e.g. rsmat.ts) it is used for
# internal computations (position, bundled_heads …) that are NOT rendered, so
# scanning those files with this pattern would produce false "present" results.
CARD_ENTITY_PATTERNS_DECLARATIVE_ONLY: list[re.Pattern[str]] = [
    re.compile(r'get_entity\([\'"]([a-z_][a-z0-9_]*)[\'"]'),
]

# File suffixes that are considered "declarative" sources: mapping objects and
# dialog definitions.  get_entity() calls in these files reference entities that
# are genuinely rendered or surfaced in the UI.
_DECLARATIVE_SUFFIXES: tuple[str, ...] = (
    ".mapping.ts",
    ".dialogs.ts",
    "dialog_func_ext.ts",
)

# Known short entity keys that must not be filtered by the noise exclusion
_SHORT_ENTITY_KEYS: frozenset[str] = frozenset({"ip"})

# Map card device folder name → canonical device name
# rsled folder contains G1 (rsled_g1.mapping.ts), G2 (rsled_g2.mapping.ts) and
# what they share (rsled.common.mapping.ts, dialogs, view elements)
# We map all three logical devices to the same folder; filtering is done by
# restricting which TS files are scanned per variant (see DEVICE_TS_FILTER).
CARD_DEVICE_FOLDERS: dict[str, str] = {
    "rsdose": "redsea/rsdose",
    "rsled_g1": "redsea/rsled",
    "rsled_g2": "redsea/rsled",
    "rsled_virtual": "redsea/rsled",
    "rsato": "redsea/rsato",
    "rsrun": "redsea/rsrun",
    "rswave": "redsea/rswave",
    "rsmat": "redsea/rsmat",
    "rspower": "redsea/rspower",
    "rscontrol": "redsea/rscontrol",
    "smartdrift": "aquamedic/smartdrift",
    "dcrunner": "aquamedic/dcrunner",
    "dcskimmer": "aquamedic/dcskimmer",
}

# Extra folders scanned for a device, on top of its own: the base class, the
# elements and the dialogs several views of one manufacturer share.
CARD_SHARED_FOLDERS: dict[str, list[str]] = {
    "smartdrift": ["aquamedic/common"],
    "dcrunner": ["aquamedic/common"],
    "dcskimmer": ["aquamedic/common"],
}

# Restrict TS file scanning per device variant.
# Key: device name. Value: set of filename patterns to INCLUDE (None = all files).
# This lets us give rsled_g1 only rsled_g1.mapping.ts and rsled_g2 only rsled_g2.mapping.ts
# (plus the files every ReefLED shares).
# Files every ReefLED variant shares: the common mapping, the dialogs, the
# device logic and the view elements (sky, beam, sliders, program editor).
_RSLED_COMMON_FILES: set[str] = {
    "rsled.common.mapping.ts",
    "rsled.dialogs.ts",
    "rsled.ts",
    "rsled_sky.ts",
    "rsled_beam.ts",
    "rsled_slider.ts",
    "rsled_program_editor.ts",
    "rsled_linked.ts",
    "index.ts",
}

DEVICE_TS_INCLUDE: dict[str, set[str] | None] = {
    "rsled_g1": _RSLED_COMMON_FILES | {"rsled_g1.mapping.ts"},
    "rsled_g2": _RSLED_COMMON_FILES | {"rsled_g2.mapping.ts"},
    "rsled_virtual": _RSLED_COMMON_FILES | {"rsled_virtual.mapping.ts"},
}

# device.dialogs.ts is imported by ALL real devices via:
#   import {dialogs_device} from "../device.dialogs"
# Its entities are therefore available to every device.
SHARED_DIALOG_FILE = "devices/device.dialogs.ts"

# Base element files that reference device entities (e.g. schedule.ts calls
# _pressButton("preview_start") which resolves via this.device.entities).
# These are scanned for all devices that use the element.
SHARED_BASE_FILES: list[str] = [
    "base/schedule.ts",
]

# Per-device extra dialog files (in addition to the shared one)
DEVICE_EXTRA_DIALOG_FILES: dict[str, list[str]] = {
    "rsdose": ["devices/redsea/rsdose/rsdose.dialogs.ts"],
}


def extract_card_entities(card_src_dir: Path) -> dict[str, set[str]]:
    """
    Returns: { device: set(entity_key) }

    For each device we collect:
      1. All entity/target/name keys from the device folder's .ts files
      2. Keys from device.dialogs.ts (common to ALL devices via import)
      3. Keys from shared base element files (e.g. schedule.ts)
      4. Keys from any per-device extra dialog files
    """
    # Step A: shared dialog entities (common to all devices)
    shared_keys: set[str] = set()
    shared_file = card_src_dir / SHARED_DIALOG_FILE
    if shared_file.exists():
        shared_keys = _extract_keys_from_ts_file(shared_file)

    # Step B: shared base element files (common to all devices)
    for rel in SHARED_BASE_FILES:
        base_file = card_src_dir / rel
        if base_file.exists():
            shared_keys.update(_extract_keys_from_ts_file(base_file))

    result: dict[str, set[str]] = {}

    for device, folder in CARD_DEVICE_FOLDERS.items():
        device_keys: set[str] = set(shared_keys)
        include_filter = DEVICE_TS_INCLUDE.get(device)  # None = include all

        # Per-device folder: all .ts files (filtered if needed), then the
        # folders it shares with the other views of its manufacturer
        for rel_folder in [folder, *CARD_SHARED_FOLDERS.get(device, [])]:
            folder_path = card_src_dir / "devices" / rel_folder
            if not folder_path.exists():
                continue
            for ts_file in folder_path.rglob("*.ts"):
                if "supplements_list" in ts_file.name:
                    continue
                if include_filter is not None and ts_file.name not in include_filter:
                    continue
                device_keys.update(_extract_keys_from_ts_file(ts_file))

        # Extra per-device dialog files
        for rel in DEVICE_EXTRA_DIALOG_FILES.get(device, []):
            extra = card_src_dir / rel
            if extra.exists():
                device_keys.update(_extract_keys_from_ts_file(extra))

        result[device] = device_keys

    return result


def _strip_comments(content: str) -> str:
    """
    Remove TypeScript/JavaScript comments from source before regex matching.

    Handles:
      - Single-line comments  //  …
      - Multi-line comments   /* … */
    String literals are NOT parsed, so a comment marker inside a string would
    be stripped too — acceptable for our entity-key extraction purpose.
    """
    # Remove /* ... */ blocks (non-greedy, DOTALL so newlines are included)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    # Remove // ... end-of-line comments
    content = re.sub(r"//[^\n]*", "", content)
    return content


# Explicit declaration, in a comment, of entities the code uses in a way the
# patterns cannot see: a key built at run time (`get_entity("port_type_" +
# port)`), an alias (a probe's main reading exposed as `probe_primary`), or a
# read in a logic file that drives the picture (a blinking overlay). Written
# next to the code that uses them:
#
#   // check-entities: uses port_type
#   // check-entities: uses power_link_up, probe_leak_detected
#
# Read before the comments are stripped, since it lives in one.
USES_DIRECTIVE_RE = re.compile(
    r"check-entities:\s*uses\s+([a-z0-9_]+(?:\s*,\s*[a-z0-9_]+)*)"
)


def _declared_keys(raw: str) -> set[str]:
    """Keys named by `check-entities: uses …` comments."""
    keys: set[str] = set()
    for m in USES_DIRECTIVE_RE.finditer(raw):
        keys.update(k.strip() for k in m.group(1).split(",") if k.strip())
    return keys


def _extract_keys_from_ts_file(path: Path) -> set[str]:
    raw = path.read_text(encoding="utf-8")
    declared = _declared_keys(raw)
    # Strip comments so that commented-out entity references are not collected
    content = _strip_comments(raw)

    # get_entity() calls are only reliable display indicators in mapping/dialog files.
    # In plain device logic files they are used for internal computations (e.g. reading
    # position or bundled_heads to drive rendering logic) and must NOT be counted as
    # "displayed" references — otherwise those entities would be wrongly marked present.
    is_declarative = any(path.name.endswith(sfx) for sfx in _DECLARATIVE_SUFFIXES)
    patterns = CARD_ENTITY_PATTERNS + (
        CARD_ENTITY_PATTERNS_DECLARATIVE_ONLY if is_declarative else []
    )

    keys: set[str] = set()
    for pattern in patterns:
        for m in pattern.finditer(content):
            k = m.group(1).strip()
            # Keep known short keys (e.g. 'ip'); skip mdi icons, CSS, single chars
            if not k:
                continue
            if k in _SHORT_ENTITY_KEYS:
                keys.add(k)
                continue
            if (
                len(k) >= 3
                and not k.startswith("mdi")
                and not k.startswith("rgb")
                and not k.startswith("rgba")
            ):
                keys.add(k)
    return keys | declared


# ---------------------------------------------------------------------------
# Step 3 – Cross-check and report
# ---------------------------------------------------------------------------

DEVICES = [
    "rsdose",
    "rsled_g1",
    "rsled_g2",
    "rsled_virtual",
    "rsato",
    "rsrun",
    "rswave",
    "rsmat",
    "rspower",
    "rscontrol",
    # ha-aquamedic-component
    *AQUAMEDIC_DEVICES,
]

# Some translation_keys are template-based (per head/pump) and the card uses
# the base key without the suffix. We strip known suffixes for comparison.
STRIP_SUFFIXES_RE = re.compile(
    r"_(head|pump|head_\d+|pump_\d+|\d+)$"
    r"|_head_\d+_\w+$"
)


def normalize_key(key: str) -> str:
    """Strip per-instance suffixes to get the base translation key."""
    return STRIP_SUFFIXES_RE.sub("", key)


# ---------------------------------------------------------------------------
# Ignore-list helpers
# ---------------------------------------------------------------------------

IgnoreList = dict[str, dict[str, list[str]]]  # { device: { platform: [key, ...] } }
DevInProgressList = list[str]  # ["rsdose", "rsmat", ...]


def load_ignore_list(path: Path) -> tuple[IgnoreList, DevInProgressList]:
    """
    Load an optional JSON ignore-list.

    Expected format::

        {
          "dev_in_progress": ["rsmat", "rsdose"],
          "ignore": {
            "rsdose": {
              "switch": ["cloud_connect", "use_cloud_api"],
              "sensor": ["mode"]
            },
            "*": {
              "button": ["fetch_config", "firmware_update", "reset"]
            }
          }
        }

    The special device key ``"*"`` applies to every device.
    Devices in "dev_in_progress" will show missing entities but won't cause exit code 1.
    """
    if not path.exists():
        return {}, []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"{YELLOW}Avertissement : impossible de lire {path} : {exc}{RESET}")
        return {}, []

    # Support both old format (direct ignore dict) and new format (with dev_in_progress)
    if "ignore" in raw or "dev_in_progress" in raw:
        ignore_list = raw.get("ignore", {})
        dev_in_progress = raw.get("dev_in_progress", [])
    else:
        # Old format: assume entire file is the ignore dict
        ignore_list = raw
        dev_in_progress = []

    return ignore_list, dev_in_progress  # type: ignore[return-value]


def _ignored_keys_for(ignore: IgnoreList, device: str, platform: str) -> set[str]:
    """Return the set of keys that are explicitly ignored for (device, platform)."""
    result: set[str] = set()
    for dev_key in (device, "*"):
        dev_block = ignore.get(dev_key, {})
        for k in dev_block.get(platform, []):
            result.add(k)
            result.add(normalize_key(k))  # also match the base key
    return result


def cross_check(
    component: dict[str, dict[str, list[str]]],
    card: dict[str, set[str]],
    ignore: IgnoreList | None = None,
    device_filter: str | None = None,
) -> dict[str, dict[str, dict[str, list[str]]]]:
    """
    Returns::

        { device: { platform: { "present": [...], "missing": [...], "ignored": [...] } } }

    If *device_filter* is set, only that device is included in the report.
    """
    if ignore is None:
        ignore = {}
    report: dict[str, dict[str, dict[str, list[str]]]] = {}

    target_devices = [device_filter] if device_filter else DEVICES
    for device in target_devices:
        report[device] = {}
        card_keys = card.get(device, set())
        platforms_data = component.get(device, {})

        for platform, trans_keys in sorted(platforms_data.items()):
            ignored_keys = _ignored_keys_for(ignore, device, platform)
            present: list[str] = []
            missing: list[str] = []
            ignored: list[str] = []

            for tk in sorted(set(trans_keys)):
                base = normalize_key(tk)
                if tk in card_keys or base in card_keys:
                    present.append(tk)
                elif tk in ignored_keys or base in ignored_keys:
                    ignored.append(tk)
                else:
                    missing.append(tk)

            report[device][platform] = {
                "present": present,
                "missing": missing,
                "ignored": ignored,
            }

    return report


# ---------------------------------------------------------------------------
# Pretty-print helpers
# ---------------------------------------------------------------------------

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
CYAN = "\033[96m"
DIM = "\033[2m"


def print_report(
    report: dict[str, dict[str, dict[str, list[str]]]],
    component: dict[str, dict[str, list[str]]],
    card: dict[str, set[str]],
    dev_in_progress: DevInProgressList | None = None,
    verbose: bool = True,
    device_filter: str | None = None,
) -> int:
    """
    Print the coverage report.

    If *device_filter* is set, only that device is shown.

    Returns:
        Number of MISSING entities that are NOT in dev_in_progress devices (i.e., actual errors).
    """
    if dev_in_progress is None:
        dev_in_progress = []

    print(f"\n{BOLD}{'=' * 70}{RESET}")
    print(f"{BOLD}  HA Reef Card  —  Components ↔ Card entity coverage report{RESET}")
    if device_filter:
        print(f"{BOLD}  Filter: {CYAN}{device_filter}{RESET}")
    print(f"{BOLD}{'=' * 70}{RESET}\n")

    total_present = 0
    total_missing = 0
    total_ignored = 0
    total_missing_errors = 0  # Missing entities NOT in dev devices
    # Per-device totals for final summary table
    dev_totals: list[
        tuple[str, int, int, int, int, bool]
    ] = []  # (device, total, present, ignored, missing, is_dev)

    target_devices = [device_filter] if device_filter else DEVICES
    for device in target_devices:
        device_data = report[device]
        dev_present = sum(len(v["present"]) for v in device_data.values())
        dev_missing = sum(len(v["missing"]) for v in device_data.values())
        dev_ignored = sum(len(v.get("ignored", [])) for v in device_data.values())
        dev_total = dev_present + dev_ignored + dev_missing
        is_dev = device in dev_in_progress

        total_present += dev_present
        total_missing += dev_missing
        total_ignored += dev_ignored
        if not is_dev:
            total_missing_errors += dev_missing

        dev_totals.append(
            (device, dev_total, dev_present, dev_ignored, dev_missing, is_dev)
        )

        status_color = GREEN if dev_missing == 0 else (YELLOW if is_dev else RED)
        ignored_note = f"  {DIM}~ {dev_ignored}{RESET}" if dev_ignored else ""
        dev_label = f" {YELLOW}[DEV]{RESET}" if is_dev else ""
        print(
            f"{BOLD}{CYAN}◆ {device.upper()}{RESET}{dev_label}  "
            f"{status_color}{dev_present} présent(s){RESET}  "
            f"{status_color if dev_missing else DIM}{dev_missing} manquant(s){RESET}"
            f"{ignored_note}"
        )

        for platform, data in sorted(device_data.items()):
            present = data["present"]
            missing = data["missing"]
            ignored = data.get("ignored", [])
            p_str = f"{GREEN}✓ {len(present)}{RESET}"
            m_color = YELLOW if is_dev and missing else (RED if missing else DIM)
            m_str = (
                f"{m_color}✗ {len(missing)}{RESET}" if missing else f"{DIM}✗ 0{RESET}"
            )
            i_str = f"  {DIM}~ {len(ignored)}{RESET}" if ignored else ""
            print(f"  {BOLD}{platform:<16}{RESET}  {p_str}  {m_str}{i_str}")

            if verbose and present:
                for k in present:
                    print(f"    {GREEN}✓{RESET} {k}")
            if missing:
                miss_color = YELLOW if is_dev else RED
                miss_label = "MISSING (DEV)" if is_dev else "MISSING"
                for k in missing:
                    print(f"    {miss_color}✗ {miss_label}:{RESET} {BOLD}{k}{RESET}")
            if ignored:
                for k in ignored:
                    print(f"    {DIM}~{RESET} IGNORE  {k}")

        print()

    # ── Summary table ───────────────────────────────────────────────────────
    grand_total = total_present + total_ignored + total_missing
    pct = (total_present / grand_total * 100) if grand_total else 0
    color = GREEN if total_missing == 0 else (YELLOW if pct > 80 else RED)

    W = 10  # column width for numbers
    print(f"{BOLD}{'─' * 70}{RESET}")
    print(
        f"{BOLD}  {'DEVICE':<12}  {'TOTAL':>{W}}  {GREEN}✓ FOUND{RESET}{BOLD}  {DIM}~ IGNORE{RESET}{BOLD}  {RED}✗ MISSING{RESET}{BOLD}{RESET}"
    )
    print(f"{BOLD}  {'─' * 12}  {'─' * W}  {'─' * W}  {'─' * W}  {'─' * W}{RESET}")
    for device, dtotal, dpresent, dignored, dmissing, is_dev in dev_totals:
        m_color = YELLOW if is_dev and dmissing else (RED if dmissing else DIM)
        dev_mark = f" {YELLOW}[DEV]{RESET}" if is_dev else ""
        print(
            f"  {BOLD}{CYAN}{device:<12}{RESET}{dev_mark if not is_dev else ''}"
            f"  {dtotal:>{W}}"
            f"  {GREEN}✓{RESET} {dpresent:<{W - 2}}"
            f"  {DIM}~{RESET} {dignored:<{W - 2}}"
            f"  {m_color}✗{RESET} {dmissing:<{W - 2}}"
        )
    print(f"{BOLD}  {'─' * 12}  {'─' * W}  {'─' * W}  {'─' * W}  {'─' * W}{RESET}")
    print(
        f"  {BOLD}{'TOTAL':<12}{RESET}"
        f"  {grand_total:>{W}}"
        f"  {GREEN}✓{RESET} {total_present:<{W - 2}}"
        f"  {DIM}~{RESET} {total_ignored:<{W - 2}}"
        f"  {RED if total_missing else DIM}✗{RESET} {total_missing:<{W - 2}}"
    )
    print(f"{BOLD}{'─' * 70}{RESET}")
    print(
        f"  {BOLD}Couverture :{RESET}  {color}{total_present}/{grand_total}  ({pct:.1f}%){RESET}"
    )
    if total_missing_errors == 0:
        print(
            f"  {GREEN}{BOLD}✓ Toutes les entités sont présentes (ou ignorées) !{RESET}"
        )
    elif total_missing_errors != total_missing:
        print(
            f"  {YELLOW}{BOLD}⚠ {total_missing - total_missing_errors} entités manquantes dans des devices en développement{RESET}"
        )
        print(
            f"  {RED}{BOLD}✗ {total_missing_errors} entités manquantes à corriger !{RESET}"
        )
    else:
        print(
            f"  {RED}{BOLD}✗ {total_missing_errors} entités manquantes à corriger !{RESET}"
        )
    print()

    return total_missing_errors


# ---------------------------------------------------------------------------
# JSON dump
# ---------------------------------------------------------------------------


def dump_json(
    component: dict[str, dict[str, list[str]]],
    card: dict[str, set[str]],
    report: dict[str, dict[str, dict[str, list[str]]]],
    out_path: Path,
    ignore: IgnoreList | None = None,
    device_filter: str | None = None,
) -> None:
    target_devices = {device_filter} if device_filter else set(DEVICES)
    data = {
        "component_entities": {
            dev: {plat: sorted(set(keys)) for plat, keys in plats.items()}
            for dev, plats in component.items()
            if dev in target_devices
        },
        "card_entities": {
            dev: sorted(keys) for dev, keys in card.items() if dev in target_devices
        },
        "coverage_report": report,
        "ignore_list": ignore or {},
    }
    out_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Résultat JSON écrit dans : {out_path}\n")


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def dump_markdown(
    report: dict[str, dict[str, dict[str, list[str]]]],
    component: dict[str, dict[str, list[str]]],
    out_path: Path,
    ignore: IgnoreList | None = None,
    device_filter: str | None = None,
) -> None:
    """Write a GitHub-flavoured Markdown report."""
    from datetime import datetime

    lines: list[str] = []
    a = lines.append

    a("# HA Reef Card — Entity coverage report")
    a("")
    a(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    if device_filter:
        a(f"\n*Filter: `{device_filter}`*")
    a("")

    target_devices = [device_filter] if device_filter else DEVICES

    # ── Global summary table ────────────────────────────────────────────────
    a("## Summary")
    a("")
    a("| Device | Total | ✅ Found | ⚪ Ignored | ❌ Missing | Coverage |")
    a("|--------|------:|---------:|----------:|----------:|----------|")

    grand_total = grand_present = grand_ignored = grand_missing = 0
    for device in target_devices:
        device_data = report[device]
        dp = sum(len(v["present"]) for v in device_data.values())
        dm = sum(len(v["missing"]) for v in device_data.values())
        di = sum(len(v.get("ignored", [])) for v in device_data.values())
        dt = dp + dm + di
        grand_total += dt
        grand_present += dp
        grand_ignored += di
        grand_missing += dm
        pct = (dp / dt * 100) if dt else 0
        bar = "🟢" if dm == 0 else ("🟡" if pct > 80 else "🔴")
        a(f"| **{device}** | {dt} | {dp} | {di} | {dm} | {bar} {pct:.0f}% |")

    grand_pct = (grand_present / grand_total * 100) if grand_total else 0
    grand_bar = "🟢" if grand_missing == 0 else ("🟡" if grand_pct > 80 else "🔴")
    a(
        f"| **TOTAL** | **{grand_total}** | **{grand_present}** | **{grand_ignored}** | **{grand_missing}** | {grand_bar} **{grand_pct:.0f}%** |"
    )
    a("")

    # ── Per-device detail ───────────────────────────────────────────────────
    a("## Detail by device")
    a("")

    for device in target_devices:
        device_data = report[device]
        dp = sum(len(v["present"]) for v in device_data.values())
        dm = sum(len(v["missing"]) for v in device_data.values())
        di = sum(len(v.get("ignored", [])) for v in device_data.values())
        status = "🟢" if dm == 0 else ("🟡" if dm < 5 else "🔴")
        a(f"### {status} {device.upper()}")
        a("")
        a("| Platform | Total | ✅ Found | ⚪ Ignored | ❌ Missing |")
        a("|----------|------:|---------:|----------:|----------:|")
        for platform, data in sorted(device_data.items()):
            pp = len(data["present"])
            pm = len(data["missing"])
            pi = len(data.get("ignored", []))
            pt = pp + pm + pi
            row_icon = "✅" if pm == 0 else "❌"
            a(f"| {row_icon} `{platform}` | {pt} | {pp} | {pi} | {pm} |")
        a("")

        # Missing entities detail (only if any)
        all_missing = [
            (plat, k)
            for plat, data in sorted(device_data.items())
            for k in data["missing"]
        ]
        if all_missing:
            a("<details>")
            a(f"<summary>❌ Missing entities ({len(all_missing)})</summary>")
            a("")
            a("| Platform | Entity key |")
            a("|----------|------------|")
            for plat, k in all_missing:
                a(f"| `{plat}` | `{k}` |")
            a("")
            a("</details>")
            a("")

        # Ignored entities detail (only if any)
        all_ignored = [
            (plat, k)
            for plat, data in sorted(device_data.items())
            for k in data.get("ignored", [])
        ]
        if all_ignored:
            a("<details>")
            a(f"<summary>⚪ Ignored entities ({len(all_ignored)})</summary>")
            a("")
            a("| Platform | Entity key |")
            a("|----------|------------|")
            for plat, k in all_ignored:
                a(f"| `{plat}` | `{k}` |")
            a("")
            a("</details>")
            a("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rapport Markdown écrit dans : {out_path}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def ensure_component(integration: Integration) -> None:
    """Clone an integration from GitHub if its directory doesn't exist."""
    if integration.root.exists():
        return

    print(f"{YELLOW}{integration.label} non trouvé à : {integration.root}{RESET}")
    print(f"Clonage depuis {integration.git_url} …")
    try:
        subprocess.run(
            ["git", "clone", "--depth=1", integration.git_url, str(integration.root)],
            check=True,
        )
        print(f"{GREEN}✓ Clonage terminé.{RESET}")
    except FileNotFoundError:
        print(
            f"{RED}Erreur : git n'est pas installé ou introuvable dans PATH.{RESET}",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(
            f"{RED}Erreur lors du clonage (code {exc.returncode}).{RESET}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not integration.component_dir.exists():
        print(
            f"{RED}Erreur : le dossier attendu n'existe pas après clonage :\n"
            f"  {integration.component_dir}{RESET}",
            file=sys.stderr,
        )
        sys.exit(1)


def integrations_for(device_filter: str | None) -> list[Integration]:
    """The integrations a run needs: all of them, or the one of a device."""
    if device_filter is None:
        return list(INTEGRATIONS)
    return [i for i in INTEGRATIONS if device_filter in i.devices]


def print_help() -> None:
    B, R, C, G, Y, D = BOLD, RESET, CYAN, GREEN, YELLOW, DIM
    script = Path(sys.argv[0]).name
    devices = ", ".join(DEVICES)
    labels = ", ".join(i.label for i in INTEGRATIONS)
    git_urls = "\n".join(f"    {D}{i.git_url}{R}" for i in INTEGRATIONS)
    print(f"""
{B}Usage:{R}
  {G}python3 {script}{R} [options]

{B}Description:{R}
  Checks that every HA entity declared in the supported integrations
  ({C}{labels}{R}) is referenced in the custom card {C}ha-reef-card{R}.

  The script must be run from {C}ha-reef-card/scripts/{R}.
  Each integration is expected next to {C}ha-reef-card{R}; one that is not
  found is cloned automatically from GitHub:
{git_urls}

  With {G}--device{R}, only the integration of that device is needed.

{B}Options:{R}
  {G}--device=<name>{R}
      Run the check for a single device only.
      Valid names: {C}{devices}{R}

  {G}--quiet{R}
      Do not list entities that are already present in the card.
      Only missing and ignored entities are shown.

  {G}--ignore=<file.json>{R}
      Load a list of entities intentionally absent from the card.
      Default: {D}scripts/check_entities_ignore.json{R} (if present).
      Format:
        {{
          "dev_in_progress": ["rsmat", "rsdose"],
          "ignore": {{
            "*":      {{ "button": ["fetch_config", "reset"] }},
            "rsdose": {{ "sensor": ["mode", "last_calibration"] }}
          }}
        }}

      {B}dev_in_progress{R}: List of devices under active development.
          Missing entities in these devices are shown as {Y}✗ MISSING (DEV){R}
          but do NOT cause exit code 1 (CI/CD will pass).

      {B}ignore{R}: Entities intentionally not implemented in the card.
          The special key {C}"*"{R} applies to every device.
          These entities are shown as {D}~ IGNORE{R}.

      {B}Old format{R}: For backward compatibility, a file containing only the
          ignore dict (without "dev_in_progress") is still supported.

  {G}--json=<file.json>{R}
      Write the full report as JSON to the given file.
      Default: {D}scripts/check_entities_report.json{R}.

  {G}--markdown{R}
      Generate a GitHub Markdown report at {D}scripts/check_entities_report.md{R}.

  {G}--markdown=<file.md>{R}
      Generate the Markdown report at the given path.

  {G}--help{R}, {G}-h{R}
      Show this message and exit.

{B}Exit Codes:{R}
  {G}0{R}  All entities present or ignored (including dev devices)
  {G}1{R}  One or more entities missing in non-dev devices

{B}Examples:{R}
  {D}# Check a single device only{R}
  python3 {script} --device=rsmat

  {D}# Full report (console + auto JSON){R}
  python3 {script}

  {D}# Suppress the list of already-present entities{R}
  python3 {script} --quiet

  {D}# Also generate a Markdown report{R}
  python3 {script} --markdown

  {D}# Use a custom ignore file{R}
  python3 {script} --ignore=../my_ignore.json

  {D}# All-in-one{R}
  python3 {script} --quiet --markdown=../COVERAGE.md --ignore=check_entities_ignore.json
""")


def main() -> None:
    verbose = "--quiet" not in sys.argv
    json_out: Path | None = None
    md_out: Path | None = None
    ignore_path: Path | None = None
    device_filter: str | None = None  # None = all devices

    for arg in sys.argv[1:]:
        if arg in ("--help", "-h"):
            print_help()
            sys.exit(0)
        elif arg.startswith("--json="):
            json_out = Path(arg.split("=", 1)[1])
        elif arg.startswith("--markdown="):
            md_out = Path(arg.split("=", 1)[1])
        elif arg == "--markdown":
            md_out = SCRIPT_DIR / "check_entities_report.md"
        elif arg.startswith("--ignore="):
            ignore_path = Path(arg.split("=", 1)[1])
        elif arg.startswith("--device="):
            device_filter = arg.split("=", 1)[1].strip()
            if device_filter not in DEVICES:
                print(
                    f"{RED}Erreur : device inconnu '{device_filter}'.{RESET}\n"
                    f"Devices disponibles : {', '.join(DEVICES)}",
                    file=sys.stderr,
                )
                sys.exit(1)

    # Default ignore file: check_entities_ignore.json next to this script
    if ignore_path is None:
        default_ignore = SCRIPT_DIR / "check_entities_ignore.json"
        if default_ignore.exists():
            ignore_path = default_ignore

    # ---- Ensure the component repos are available ----
    integrations = integrations_for(device_filter)
    for integration in integrations:
        ensure_component(integration)
        print(f"  Composant : {integration.component_dir}")
    print(f"  Card      : {CARD_DIR}")
    if device_filter:
        print(f"  Device    : {CYAN}{device_filter}{RESET}  (filtre actif)")

    ignore: IgnoreList = {}
    dev_in_progress: DevInProgressList = []
    if ignore_path is not None:
        ignore, dev_in_progress = load_ignore_list(ignore_path)
        ignore_count = sum(len(p) for d in ignore.values() for p in d.values())
        if ignore:
            print(f"  Ignore    : {ignore_path}  ({ignore_count} entité(s) ignorée(s))")
        if dev_in_progress:
            print(
                f"  Dev       : {len(dev_in_progress)} device(s) en développement : {', '.join(dev_in_progress)}"
            )
    print()

    print("Extraction des entités des composants (AST)…")
    component = extract_all_component_entities(integrations)

    print("Extraction des entités de la card (TypeScript)…")
    card = extract_card_entities(CARD_DIR)

    print("Vérification croisée…")
    report = cross_check(component, card, ignore=ignore, device_filter=device_filter)

    error_count = print_report(
        report,
        component,
        card,
        dev_in_progress=dev_in_progress,
        verbose=verbose,
        device_filter=device_filter,
    )

    if json_out:
        dump_json(
            component,
            card,
            report,
            json_out,
            ignore=ignore,
            device_filter=device_filter,
        )
    else:
        # Dump JSON next to this script (ha-reef-card/scripts/)
        default_json = SCRIPT_DIR / "check_entities_report.json"
        dump_json(
            component,
            card,
            report,
            default_json,
            ignore=ignore,
            device_filter=device_filter,
        )

    if md_out:
        dump_markdown(
            report, component, md_out, ignore=ignore, device_filter=device_filter
        )

    # Exit with error code 1 if there are missing entities (excluding dev devices)
    if error_count > 0:
        print(f"\n{RED}Échec : {error_count} entité(s) manquante(s) à corriger.{RESET}")
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

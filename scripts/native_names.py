"""Resolve Lua-callable names from FiveM's installed wrappers, never C-name heuristics."""
import copy
import hashlib
import json
import os
import re
import sys

import paths
from i18n import t

FUNCTION = re.compile(r"function Global\.(\w+)\(([^\n]*)\)\s*\n(.*?)\nend", re.S)
INVOKE = re.compile(r"_in(?:2)?\(\s*(?:_gn\(\s*)?(0x[0-9a-fA-F]+)")
ALIAS = re.compile(r"^Global\.(\w+)\s*=\s*Global\.(\w+)\s*$", re.M)
FILES = {"client": "natives_universal.lua", "server": "natives_server.lua"}


def read_wrappers(text):
    """Read definitions and explicit aliases in assignment order without executing Lua."""
    events = []
    for match in FUNCTION.finditer(text):
        invocation = INVOKE.search(match[3])
        if not invocation:
            raise ValueError(match[1])
        parameters = [name.strip() for name in match[2].split(",") if name.strip()]
        events.append((match.start(), match[1], {"hash": int(invocation[1], 16), "params": parameters}))
    events.extend((match.start(), match[1], match[2]) for match in ALIAS.finditer(text))
    wrappers = {}
    for _, name, value in sorted(events):
        if isinstance(value, str):
            if value not in wrappers:
                raise ValueError(name)
            value = wrappers[value]
        wrappers[name] = value
    if not wrappers:
        raise ValueError("Global")
    return wrappers


def runtime_bindings(runtime_dir=None):
    if runtime_dir is None:
        runtime_dir, reason = paths.resolve("fivem")
        if runtime_dir is None:
            print(t("native_runtime_missing", reason=reason), file=sys.stderr)
            raise SystemExit(2)
    nested = os.path.join(runtime_dir, "citizen", "scripting", "lua")
    if os.path.isdir(nested):
        runtime_dir = nested
    bindings = {}
    sources = {}
    for side, filename in FILES.items():
        path = os.path.join(runtime_dir, filename)
        if not os.path.isfile(path):
            print(t("native_runtime_missing", reason=filename), file=sys.stderr)
            raise SystemExit(2)
        try:
            with open(path, "rb") as stream:
                data = stream.read()
            wrappers = read_wrappers(data.decode("utf-8-sig"))
        except (OSError, UnicodeError, ValueError) as error:
            print(t("native_runtime_invalid", reason=str(error)), file=sys.stderr)
            raise SystemExit(3)
        sources[side] = {"file": filename, "sha256": hashlib.sha256(data).hexdigest(), "names": len(wrappers)}
        for name, wrapper in wrappers.items():
            bindings.setdefault(wrapper["hash"], {}).setdefault(name, {})[side] = {
                "hash": "0x{:016X}".format(wrapper["hash"]), "params": wrapper["params"],
            }
    return bindings, sources


def side_name(sides):
    return "shared" if "client" in sides and "server" in sides else next(iter(sides))


def merge_record(records, key, record):
    """Keep both bindings when one Lua name has different client/server hashes."""
    if key not in records:
        records[key] = record
        return
    previous = records[key]
    if (record.get("sources") != ["lua-runtime"] and record.get("metadataLua") == key
            and previous.get("metadataLua") != key):
        previous, record = record, previous
        records[key] = previous
    for name, sides in record["luaBindings"].items():
        previous["luaBindings"].setdefault(name, {}).update(sides)
    variants = previous.setdefault("variants", {})
    variants[previous["hash"]] = {"params": previous["params"], "results": previous["results"]}
    variants[record["hash"]] = {"params": record["params"], "results": record["results"]}
    variants.update(record.get("variants", {}))
    hashes = previous.get("altHash", []) + record.get("altHash", []) + [record["hash"]]
    previous["altHash"] = sorted(set(hashes) - {previous["hash"]})
    previous["apiset"] = side_name({side for sides in previous["luaBindings"].values() for side in sides})


def apply_runtime_names(records, bindings):
    result = {}
    covered = set()
    for old_key, original in records.items():
        record = copy.deepcopy(original)
        hashes = {int(value, 16) for value in [record["hash"]] + record.get("altHash", [])}
        actual = {}
        for native_hash in hashes:
            for name, sides in bindings.get(native_hash, {}).items():
                actual.setdefault(name, {}).update(sides)
            covered.add(native_hash)
        record["luaBindings"] = actual
        record["luaVerified"] = bool(actual)
        record["metadataLua"] = record.get("metadataLua", record["lua"])
        if actual:
            key = record["lua"] if record["lua"] in actual else min(actual, key=lambda name: (name.startswith("N_0x"), len(name), name))
            record["lua"] = key
            record["apiset"] = side_name({side for sides in actual.values() for side in sides})
        else:
            key = "metadata:" + record["hash"]
        merge_record(result, key, record)
    for native_hash, actual in bindings.items():
        if native_hash in covered:
            continue
        name = min(actual, key=lambda value: (value.startswith("N_0x"), len(value), value))
        parameters = next(iter(actual[name].values()))["params"]
        record = {
            "lua": name, "metadataLua": name, "name": name, "hash": "0x{:016X}".format(native_hash), "ns": "RUNTIME",
            "apiset": side_name({side for sides in actual.values() for side in sides}),
            "params": [{"name": parameter, "type": "?"} for parameter in parameters],
            "results": "?", "sources": ["lua-runtime"], "luaVerified": True, "luaBindings": actual,
        }
        merge_record(result, name, record)
    for record in result.values():
        record["luaAliases"] = sorted(set(record["luaBindings"]) - {record["lua"]})
    return result


def binding_record(record, name, side=None):
    sides = record["luaBindings"][name]
    chosen = side if side in sides else "client" if "client" in sides else "server"
    binding = sides[chosen]
    metadata = record if int(record["hash"], 16) == int(binding["hash"], 16) else {}
    for native_hash, variant in record.get("variants", {}).items():
        if int(native_hash, 16) == int(binding["hash"], 16):
            metadata = variant
    types = {parameter["name"]: parameter.get("type", "?") for parameter in metadata.get("params", [])}
    return dict(record, lua=name, hash=binding["hash"], apiset=side_name(sides), results=metadata.get("results", "?"),
                params=[{"name": parameter, "type": types.get(parameter, "?")} for parameter in binding["params"]])


def callable_index(records, side=None):
    names = {}
    for record in records.values():
        for name, sides in record["luaBindings"].items():
            candidate = dict(record, lua=name, luaBindings={name: copy.deepcopy(sides)},
                             variants=copy.deepcopy(record.get("variants", {})))
            merge_record(names, name, candidate)
    return {name: binding_record(record, name, side) for name, record in names.items()}


def reference_record(record, reference, side=None):
    if not record["luaVerified"]:
        return record
    if not reference.lower().startswith("0x"):
        return binding_record(record, record["lua"], side)
    native_hash = int(reference, 16)
    candidates = {name: {api: binding for api, binding in sides.items() if int(binding["hash"], 16) == native_hash}
                  for name, sides in record["luaBindings"].items()}
    candidates = {name: sides for name, sides in candidates.items() if sides}
    if not candidates:
        return dict(record, luaVerified=False)
    name = record["lua"] if record["lua"] in candidates else min(candidates, key=lambda value: (value.startswith("N_0x"), len(value), value))
    sides = candidates[name]
    chosen = side if side in sides else "client" if "client" in sides else "server"
    return dict(binding_record(record, name, chosen), apiset=side_name(sides))


def load_database(path):
    if not os.path.isfile(path):
        print(t("layer_missing", file=path, cmd="python scripts/build_index.py --fetch"), file=sys.stderr)
        raise SystemExit(2)
    try:
        with open(path, encoding="utf-8") as stream:
            records = json.load(stream)
    except (OSError, ValueError) as error:
        print(t("native_index_invalid", reason=str(error)), file=sys.stderr)
        raise SystemExit(3)
    bindings, _ = runtime_bindings()
    return apply_runtime_names(records, bindings)

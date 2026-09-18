"""Offline admission gate for complete, result-only MCP tools/list snapshots.

No model, transport, tool execution, or maliciousness classifier is implemented.
"""
from dataclasses import dataclass
import hashlib
import json
import math

MAX_BYTES = 65536
MAX_TOOLS = 100
MAX_DEPTH = 32


class InvalidMetadata(ValueError):
    pass


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidMetadata("duplicate_json_key")
        result[key] = value
    return result


def _constant(_):
    raise InvalidMetadata("nonfinite_number")


def _bounded(value, depth=0):
    if depth > MAX_DEPTH:
        raise InvalidMetadata("too_deep")
    if isinstance(value, float) and not math.isfinite(value):
        raise InvalidMetadata("nonfinite_number")
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise InvalidMetadata("invalid_unicode") from exc
    if isinstance(value, dict):
        for key, item in value.items():
            _bounded(key, depth + 1)
            _bounded(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _bounded(item, depth + 1)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_tools(raw):
    """Validate our documented subset; preserve every tool-definition field."""
    if not isinstance(raw, str):
        raise InvalidMetadata("expected_text")
    try:
        if len(raw.encode("utf-8")) > MAX_BYTES:
            raise InvalidMetadata("too_large")
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
        _bounded(value)
    except InvalidMetadata:
        raise
    except (UnicodeError, RecursionError, ValueError) as exc:
        raise InvalidMetadata("invalid_json") from exc
    if not isinstance(value, dict):
        raise InvalidMetadata("expected_object")
    if "nextCursor" in value:
        raise InvalidMetadata("pagination_unsupported")
    if set(value) != {"tools"}:
        raise InvalidMetadata("expected_complete_tools_result")
    tools = value["tools"]
    if not isinstance(tools, list) or len(tools) > MAX_TOOLS:
        raise InvalidMetadata("invalid_tool_list")
    names = set()
    for tool in tools:
        if not isinstance(tool, dict):
            raise InvalidMetadata("invalid_tool")
        name = tool.get("name")
        if not isinstance(name, str) or not name.strip():
            raise InvalidMetadata("invalid_tool_name")
        if name in names:
            raise InvalidMetadata("duplicate_tool_name")
        names.add(name)
        for field in ("description", "title"):
            if field in tool and not isinstance(tool[field], str):
                raise InvalidMetadata("invalid_" + field)
        for field in ("inputSchema", "outputSchema"):
            if field == "inputSchema" or field in tool:
                schema = tool.get(field)
                if not isinstance(schema, dict) or schema.get("type") != "object":
                    raise InvalidMetadata("invalid_" + field)
        if "annotations" in tool and not isinstance(tool["annotations"], dict):
            raise InvalidMetadata("invalid_annotations")
    return sorted(tools, key=lambda tool: tool["name"])


def _identity(identity):
    if not isinstance(identity, str) or not identity.strip() or len(identity) > 200:
        raise InvalidMetadata("invalid_host_identity")
    _bounded(identity)


@dataclass(frozen=True)
class Snapshot:
    """Trusted host-owned review record. This is a digest, not a signature."""
    host_identity: str
    canonical_tools: str

    @property
    def fingerprint(self):
        return digest(canonical({"host_identity": self.host_identity,
                                 "tools": json.loads(self.canonical_tools)}))


def review_snapshot(raw, host_identity):
    """Explicit operator action; admission never calls this to auto-enroll."""
    _identity(host_identity)
    return Snapshot(host_identity, canonical(parse_tools(raw)))


def definition_fingerprint(tools):
    return digest(canonical(tools))


def same_definitions(reviewed, current):
    return definition_fingerprint(reviewed) == definition_fingerprint(current)


def changed_paths(before, after, path=""):
    """Operator-only JSON-pointer-like diff. Values never enter diagnostics."""
    if type(before) is not type(after):
        return [path or "/"]
    if isinstance(before, dict):
        out = []
        for key in sorted(set(before) | set(after)):
            part = key.replace("~", "~0").replace("/", "~1")
            child = path + "/" + part
            if key not in before or key not in after:
                out.append(child)
            else:
                out.extend(changed_paths(before[key], after[key], child))
        return out
    if isinstance(before, list):
        if len(before) != len(after):
            return [path or "/"]
        return [p for i, (a, b) in enumerate(zip(before, after))
                for p in changed_paths(a, b, path + "/" + str(i))]
    return [] if before == after else [path or "/"]


@dataclass(frozen=True)
class Admission:
    accepted: bool
    reason: str
    paths: tuple
    current_fingerprint: str | None
    model_input_json: str


def admit(raw, host_identity, snapshot, mode):
    """Only model_input_json belongs at the model boundary; paths are operator-only."""
    if mode not in ("name_only", "snapshot"):
        raise ValueError("unknown mode")

    def reject(reason, paths=(), fingerprint=None):
        return Admission(False, reason, tuple(paths), fingerprint, '{"tools":[]}')

    try:
        _identity(host_identity)
        current = parse_tools(raw)
    except InvalidMetadata as exc:
        return reject(str(exc))
    fingerprint = digest(canonical({"host_identity": host_identity, "tools": current}))
    if host_identity != snapshot.host_identity:
        return reject("host_identity_changed", ("/host_identity",), fingerprint)
    reviewed = json.loads(snapshot.canonical_tools)
    before = {t["name"]: t for t in reviewed}
    after = {t["name"]: t for t in current}
    paths = changed_paths(before, after, "/tools")
    if set(before) != set(after):
        return reject("tool_names_changed", paths, fingerprint)
    if mode == "snapshot" and not same_definitions(reviewed, current):
        return reject("metadata_changed", paths, fingerprint)
    # Serialize the exact validated copy; do not refetch or return a mutable alias.
    return Admission(True, "accepted", tuple(paths), fingerprint,
                     canonical({"tools": current}))

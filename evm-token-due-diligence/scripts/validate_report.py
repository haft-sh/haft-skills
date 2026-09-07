#!/usr/bin/env python3
"""Offline evidence-packet consistency checks; never signs or makes network calls."""

import hashlib
import json
import re
import sys
from pathlib import Path

MAX_JSON = 4 * 1024 * 1024
MAX_FILE = 64 * 1024 * 1024
MAX_TOTAL = 1024 * 1024 * 1024
ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}")
HASH = re.compile(r"0x[0-9a-fA-F]{64}")
QUANTITY = re.compile(r"0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)")


class PacketError(ValueError):
    """Safe static validation message, without captured source values."""


def require(condition, message):
    if not condition:
        raise PacketError(message)


def obj(value):
    require(isinstance(value, dict), "expected JSON object")
    return value


def items(value):
    require(isinstance(value, list) and value, "expected nonempty list")
    return value


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def matches(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def read_json(path):
    with path.open("rb") as stream:
        raw = stream.read(MAX_JSON + 1)
    require(len(raw) <= MAX_JSON, "JSON exceeds byte budget")
    return json.loads(raw, object_pairs_hook=unique_object,
                      parse_constant=lambda _: require(False, "non-finite JSON number"))


def quantity(value):
    require(matches(QUANTITY, value), "invalid RPC quantity")
    return int(value, 16)


def validate_packet(report, base):
    obj(report)
    require(report.get("schema_version") == "evm-diligence-evidence-v1", "unsupported evidence schema")
    target = obj(report.get("target"))
    identities = []
    for role in ("requested", "queried", "reported"):
        identity = obj(target.get(role))
        require(integer(identity.get("chain_id"), 1), "invalid target chain")
        require(matches(ADDRESS, identity.get("address")), "invalid target address")
        require(int(identity["address"], 16) != 0, "zero token target")
        identities.append((identity["chain_id"], identity["address"].lower()))
    require(len(set(identities)) == 1, "target chain/address mismatch")
    chain, address = identities[0]

    metadata = obj(report.get("metadata"))
    observed, reported = obj(metadata.get("observed")), obj(metadata.get("reported"))
    unresolved = obj(metadata.get("unresolved"))
    fields = {"name", "symbol", "decimals", "supply"}
    require(set(unresolved) <= fields and all(nonempty(reason) for reason in unresolved.values()),
            "invalid unresolved metadata reasons")
    for field in fields:
        require(field in observed and field in reported, "missing metadata field")
        for value in (observed[field], reported[field]):
            valid = (nonempty(value) if field in ("name", "symbol") else
                     integer(value) and value <= 255 if field == "decimals" else
                     matches(re.compile(r"(?:0|[1-9][0-9]*)"), value))
            require(valid or (value is None and field in unresolved), "invalid metadata value")
        require(observed[field] == reported[field] or field in unresolved, "unexplained metadata mismatch")

    sources = {}
    paths = set()
    total = 0
    for source in items(report.get("sources")):
        obj(source)
        source_id, relative = source.get("id"), source.get("path")
        require(nonempty(source_id) and source_id not in sources, "duplicate/invalid source id")
        require(nonempty(relative) and not Path(relative).is_absolute(), "source must use relative path")
        path = (base / relative).resolve()
        require(path.is_relative_to(base) and path not in paths and path.is_file(),
                "missing, duplicate or escaping source path")
        size = path.stat().st_size
        total += size
        require(integer(source.get("bytes")) and size == source["bytes"], "source byte length mismatch")
        require(size <= MAX_FILE and total <= MAX_TOTAL, "source byte budget exceeded")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            consumed = 0
            while chunk := stream.read(1024 * 1024):
                consumed += len(chunk)
                require(consumed <= size, "source changed while reading")
                digest.update(chunk)
        require(consumed == size and digest.hexdigest() == source.get("sha256"), "source SHA-256 mismatch")
        sources[source_id] = (path, digest.hexdigest())
        paths.add(path)

    def refs(value):
        require(all(isinstance(key, str) and key in sources for key in items(value)), "unknown evidence reference")

    def rpc(source_id, method):
        require(isinstance(source_id, str) and source_id in sources, "missing RPC source")
        path, digest = sources[source_id]
        # Bind the bytes parsed here, not just an earlier file-hash observation.
        with path.open("rb") as stream:
            raw = stream.read(MAX_JSON + 1)
        require(len(raw) <= MAX_JSON and hashlib.sha256(raw).hexdigest() == digest, "RPC source changed/oversized")
        capture = obj(json.loads(raw, object_pairs_hook=unique_object))
        request, response = obj(capture.get("request")), obj(capture.get("response"))
        require(request.get("method") == method, "wrong RPC method")
        require(type(request.get("id")) in (int, str) and "id" in response and type(request["id"]) is type(response["id"])
                and request["id"] == response["id"], "RPC response id mismatch")
        require("error" not in response and "result" in response, "RPC error/missing result")
        require(isinstance(request.get("params"), list), "RPC params missing")
        return request["params"], response["result"]

    pin = obj(report.get("pin"))
    require(pin.get("chain_id") == chain and type(pin.get("chain_id")) is int, "pin chain mismatch")
    require(integer(pin.get("number")) and integer(pin.get("timestamp"), 1), "invalid pin number/time")
    require(matches(HASH, pin.get("hash")) and int(pin["hash"], 16) != 0, "invalid pin hash")
    params, chain_result = rpc(pin.get("chain_source"), "eth_chainId")
    require(params == [] and quantity(chain_result) == chain, "captured chain mismatch")
    # Capture the header by hash; do not accept a user-authored header object.
    params, header = rpc(pin.get("header_source"), "eth_getBlockByHash")
    obj(header)
    require(len(params) == 2 and params[0] == pin["hash"] and params[1] is False, "header request not bound to pin")
    require(quantity(header.get("number")) == pin["number"]
            and header.get("hash") == pin["hash"]
            and quantity(header.get("timestamp")) == pin["timestamp"], "captured header mismatch")

    target_seen = False
    for scope in items(report.get("scope_addresses")):
        obj(scope)
        require(type(scope.get("chain_id")) is int and scope["chain_id"] == chain, "scope chain mismatch")
        require(matches(ADDRESS, scope.get("address")) and nonempty(scope.get("role")), "invalid scope")
        refs(scope.get("provenance_sources"))
        target_seen |= scope["address"].lower() == address
        state = scope.get("runtime_status")
        require(state in ("code", "no_code", "unresolved"), "invalid runtime status")
        if state == "unresolved":
            require(nonempty(scope.get("reason")), "unresolved runtime needs reason")
            continue
        params, code = rpc(scope.get("runtime_source"), "eth_getCode")
        require(len(params) == 2 and isinstance(params[0], str)
                and params[0].lower() == scope["address"].lower(), "runtime target mismatch")
        selector = obj(params[1])
        require(set(selector) == {"blockHash", "requireCanonical"}
                and selector["blockHash"] == pin["hash"] and selector["requireCanonical"] is True,
                "runtime call must use canonical block-hash selector")
        require(matches(re.compile(r"0x(?:[0-9a-fA-F]{2})*"), code), "invalid runtime bytes")
        require((code != "0x") == (state == "code"), "runtime status mismatch")
    require(target_seen, "target absent from scope")

    finding_ids = set()
    for finding in items(report.get("findings")):
        obj(finding)
        require(nonempty(finding.get("id")) and finding["id"] not in finding_ids, "invalid/duplicate finding id")
        finding_ids.add(finding["id"])
        require(nonempty(finding.get("claim")), "empty finding")
        refs(finding.get("source_ids"))
        require(finding.get("confidence") in ("high", "medium", "low"), "invalid confidence")
        require(finding.get("coverage") in ("complete", "partial", "unknown"), "invalid coverage")
        require(finding.get("assessment") in ("pass", "risk", "unresolved"), "invalid assessment")
        require(finding["assessment"] != "pass" or finding["coverage"] == "complete",
                "partial/unknown coverage cannot be a pass")
    safety = obj(report.get("safety"))
    require(safety.get("no_real_signing") is True and safety.get("no_broadcast") is True,
            "missing no-signing/no-broadcast declarations")
    require(safety.get("fork_mode") in ("none", "isolated_unsigned"), "invalid fork restriction")


def validate_report(report_path):
    try:
        path = Path(report_path).resolve()
        validate_packet(read_json(path), path.parent)
        return True, []
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        # Do not echo raw source values, provider errors or credential-bearing paths.
        message = str(error) if isinstance(error, PacketError) else type(error).__name__
        return False, [message]


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 validate_report.py <manifest.json>")
        return 1
    ok, errors = validate_report(sys.argv[1])
    print("PASS: Evidence packet is internally consistent." if ok else "FAIL: " + "; ".join(errors))
    if ok:
        print("Not proof of RPC honesty, ABI correctness, report prose, coverage, ownership or investment safety.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

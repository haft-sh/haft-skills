#!/usr/bin/env python3
"""Synthetic acceptance/failure cases. No RPC, database or real token reads."""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from validate_report import validate_report

TOKEN = "0x" + "12" * 20
BLOCK = "0x" + hashlib.sha256(b"synthetic header, not chain evidence").hexdigest()


class EvidenceValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.report = {
            "schema_version": "evm-diligence-evidence-v1",
            "target": {role: {"chain_id": 1, "address": TOKEN} for role in ("requested", "queried", "reported")},
            "metadata": {"observed": {"name": "Synthetic", "symbol": "TEST", "decimals": 18, "supply": "1000"},
                         "reported": {"name": "Synthetic", "symbol": "TEST", "decimals": 18, "supply": "1000"},
                         "unresolved": {}},
            "pin": {"chain_id": 1, "number": 123, "hash": BLOCK, "timestamp": 1700000000,
                    "header_source": "header", "chain_source": "chain"},
            "sources": [],
            "scope_addresses": [{"chain_id": 1, "address": TOKEN, "role": "target",
                                 "provenance_sources": ["code"], "runtime_status": "code", "runtime_source": "code"}],
            "findings": [{"id": "F1", "claim": "Synthetic target has nonempty runtime at synthetic pin.",
                          "source_ids": ["code"], "confidence": "high", "coverage": "complete", "assessment": "pass"}],
            "safety": {"no_real_signing": True, "no_broadcast": True, "fork_mode": "none"},
        }
        self.captures = {
            "chain": self.rpc("eth_chainId", [], "0x1"),
            "header": self.rpc("eth_getBlockByHash", [BLOCK, False],
                               {"number": "0x7b", "hash": BLOCK, "timestamp": hex(1700000000)}),
            "code": self.rpc("eth_getCode", [TOKEN, {"blockHash": BLOCK, "requireCanonical": True}], "0x6000"),
        }
        for name in self.captures:
            self.save_source(name)

    @staticmethod
    def rpc(method, params, result):
        return {"request": {"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                "response": {"jsonrpc": "2.0", "id": 1, "result": result}}

    def save_source(self, name):
        raw = json.dumps(self.captures[name]).encode()
        (self.base / (name + ".json")).write_bytes(raw)
        self.report["sources"] = [s for s in self.report["sources"] if s["id"] != name]
        self.report["sources"].append({"id": name, "path": name + ".json", "bytes": len(raw),
                                       "sha256": hashlib.sha256(raw).hexdigest()})

    def check(self, report=None):
        path = self.base / "manifest.json"
        path.write_text(json.dumps(self.report if report is None else report))
        return validate_report(path)

    def test_valid_and_cli(self):
        self.assertEqual(self.check(), (True, []))
        cli = subprocess.run([sys.executable, str(Path(__file__).with_name("validate_report.py")),
                              str(self.base / "manifest.json")], capture_output=True, text=True)
        self.assertEqual(cli.returncode, 0)
        self.assertIn("Not proof of RPC honesty", cli.stdout)

    def test_identity_and_pin_failures(self):
        cases = [
            ("target", "queried", "chain_id", 2),
            ("target", "reported", "address", "0x" + "34" * 20),
            ("target", "queried", "address", None),
            ("target", "requested", "chain_id", True),
            ("pin", None, "number", 124),
            ("pin", None, "hash", "0x" + "00" * 32),
            ("pin", None, "timestamp", 1700000001),
        ]
        for outer, inner, key, value in cases:
            with self.subTest(case=(outer, inner, key)):
                changed = copy.deepcopy(self.report)
                (changed[outer][inner] if inner else changed[outer])[key] = value
                self.assertFalse(self.check(changed)[0])

    def test_hashed_but_inconsistent_rpc_rejected(self):
        mutations = [
            ("chain", lambda x: x["response"].update(result="0x2")),
            ("header", lambda x: x["response"]["result"].update(number="0x7c")),
            ("header", lambda x: x["response"]["result"].update(timestamp="0x1")),
            ("header", lambda x: x["request"].update(params=["latest", False])),
            ("code", lambda x: x["request"].update(params=["0x" + "34" * 20, x["request"]["params"][1]])),
            ("code", lambda x: x["request"].update(params=[TOKEN, "latest"])),
            ("code", lambda x: x["response"].update(result="0x")),
            ("code", lambda x: x["response"].update(error={"message": "synthetic provider failure"})),
            ("code", lambda x: x["response"].update(id=2)),
            ("code", lambda x: x["request"]["params"][1].update(requireCanonical=1)),
            ("header", lambda x: x["request"].update(params=[BLOCK, 0])),
        ]
        original = copy.deepcopy(self.captures)
        for name, mutate in mutations:
            with self.subTest(source=name, mutation=mutate):
                self.captures = copy.deepcopy(original)
                for key in self.captures:
                    self.save_source(key)
                mutate(self.captures[name])
                self.save_source(name)
                self.assertFalse(self.check()[0])

    def test_unknown_checks_cannot_pass(self):
        for coverage in ("unknown", "partial"):
            with self.subTest(coverage=coverage):
                self.report["findings"][0]["coverage"] = coverage
                self.report["findings"][0]["assessment"] = "pass"
                self.assertFalse(self.check()[0])
                self.report["findings"][0]["assessment"] = "unresolved"
                self.assertTrue(self.check()[0])

    def test_metadata_mismatch_requires_explicit_reason(self):
        self.report["metadata"]["reported"]["symbol"] = "DIFFERENT"
        self.assertFalse(self.check()[0])
        self.report["metadata"]["unresolved"]["symbol"] = "Explicit unresolved mismatch; not silently normalized."
        self.assertTrue(self.check()[0])
        self.report["metadata"]["observed"]["decimals"] = True
        self.assertFalse(self.check()[0])

    def test_missing_corrupt_duplicate_and_escaping_sources(self):
        original = copy.deepcopy(self.report)
        for change in (
            lambda r: r["sources"][0].update(sha256="0" * 64),
            lambda r: r["sources"][0].update(bytes=1),
            lambda r: r["sources"][0].update(path="missing.json"),
            lambda r: r["sources"][0].update(path="../outside.json"),
            lambda r: r["sources"][0].update(path=str(self.base / "chain.json")),
            lambda r: r["sources"].append(copy.deepcopy(r["sources"][0])),
            lambda r: r["findings"][0].update(source_ids=["unlisted"]),
            lambda r: r["scope_addresses"][0].update(chain_id=2),
            lambda r: r["safety"].update(no_broadcast="true"),
        ):
            with self.subTest(mutation=change):
                candidate = copy.deepcopy(original)
                change(candidate)
                self.assertFalse(self.check(candidate)[0])
        (self.base / "chain.json").write_text("{}")
        self.assertFalse(self.check()[0])

    def test_symlink_escape_and_budgets(self):
        with tempfile.TemporaryDirectory() as outside:
            destination = Path(outside) / "outside.json"
            destination.write_bytes((self.base / "chain.json").read_bytes())
            (self.base / "escape.json").symlink_to(destination)
            candidate = copy.deepcopy(self.report)
            candidate["sources"][0]["path"] = "escape.json"
            self.assertFalse(self.check(candidate)[0])
        with patch("validate_report.MAX_FILE", 1):
            self.assertFalse(self.check()[0])
        with patch("validate_report.MAX_TOTAL", 1):
            self.assertFalse(self.check()[0])

    def test_malformed_documents_do_not_crash(self):
        for value in ([], {}, "bad", {"schema_version": "evm-diligence-evidence-v1", "target": []}):
            with self.subTest(document=value):
                self.assertFalse(self.check(value)[0])
        path = self.base / "manifest.json"
        for raw in ('{"a": 1, "a": 2}', '{"a": NaN}', "{", "[]"):
            path.write_text(raw)
            self.assertFalse(validate_report(path)[0])
        self.assertFalse(validate_report(self.base / "absent.json")[0])
        self.assertFalse(validate_report(self.base)[0])


if __name__ == "__main__":
    unittest.main()

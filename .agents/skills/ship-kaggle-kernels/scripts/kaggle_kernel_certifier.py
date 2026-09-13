#!/usr/bin/env python3
"""Fail-closed local simulator and certifier for Kaggle kernel packages.

The implementation is standard-library-only so the certifier itself does not inherit a
project's dependency failures. Project-specific facts live in a JSON profile.
"""

from __future__ import annotations

import argparse
import ast
import copy
import csv
import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

SCHEMA = "ship-kaggle-kernels.profile.v1"
RECEIPT_SCHEMA = "ship-kaggle-kernels.certification.v1"
KAGGLE_CLI_SAVE_KERNEL_TRANSPORT = "kaggle-cli-save-kernel.v1"
REQUIRED_ROLES = {"tiny", "stratified", "stress", "expansive"}
DEFAULT_FORBIDDEN = (".rglob(", "os.walk(", '.glob("**', ".glob('**")
NETWORK_FRAGMENTS = (
    "requests.get(",
    "requests.post(",
    "urllib.request.urlopen(",
    "subprocess.run([\"curl\"",
    "subprocess.run(['curl'",
    "subprocess.run([\"wget\"",
    "subprocess.run(['wget'",
)
ALLOWED_KINDS = {"file", "json", "jsonl", "csv", "zip", "mp4"}
NUMERIC_NAMESPACE_FAIL_FAULTS = {
    "numeric_missing_index",
    "numeric_extra_index",
    "numeric_alias_index",
}
NUMERIC_NAMESPACE_PASS_FAULTS = {"numeric_lexical_order"}
EXPECTED_FAIL_FAULTS = {
    "missing_mount",
    "missing_required_file",
    "corrupt_required_file",
} | NUMERIC_NAMESPACE_FAIL_FAULTS
EXPECTED_PASS_FAULTS = {"duplicate_basename"} | NUMERIC_NAMESPACE_PASS_FAULTS
REQUIRED_STEP0_INVARIANTS = {
    "input_identity",
    "inventory",
    "path_topology",
    "cardinality",
}
LINKER_ENVIRONMENT_VARIABLES = {
    "LD_LIBRARY_PATH",
    "LD_PRELOAD",
    "LD_AUDIT",
    "LD_DEBUG",
    "LD_DEBUG_OUTPUT",
}
LMT_POLICY_BEGIN = "<!-- LMT_POLICY_JSON_BEGIN -->"
LMT_POLICY_END = "<!-- LMT_POLICY_JSON_END -->"
CONTROL_HOST_PATH_PATTERNS = (
    re.compile(r"/(?:Users|home)/[^\s\"']+"),
    re.compile(r"/(?:opt/homebrew|private/tmp|private/var/folders|var/folders)/[^\s\"']*"),
    re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/][^\s\"']+"),
)


class CertifierError(RuntimeError):
    """Profile or simulator contract violation."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory_records(root: Path) -> list[dict[str, Any]]:
    if not root.is_dir():
        raise CertifierError(f"inventory root is not a directory: {root}")
    records: list[dict[str, Any]] = []
    symlinks = sorted(p for p in root.rglob("*") if p.is_symlink())
    if symlinks:
        rendered = ", ".join(path.relative_to(root).as_posix() for path in symlinks[:10])
        raise CertifierError(f"inventory contains symlinks: {rendered}")
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return records


def inventory_sha256(root: Path) -> str:
    return sha256_bytes(canonical_json(inventory_records(root)))


def numeric_namespace_expected_names(contract: dict[str, Any]) -> list[str]:
    """Return the canonical numeric order for one exclusive direct-entry namespace."""

    template = contract.get("filename_template")
    first_index = contract.get("first_index")
    count = contract.get("count")
    if not isinstance(template, str) or template.count("{index}") != 1:
        raise CertifierError("numeric filename_template must contain {index} exactly once")
    remainder = template.replace("{index}", "")
    if "{" in remainder or "}" in remainder:
        raise CertifierError("numeric filename_template may contain no other format fields")
    if "/" in template or "\\" in template or template in {".", ".."}:
        raise CertifierError("numeric filename_template must be one basename")
    if (
        not isinstance(first_index, int)
        or isinstance(first_index, bool)
        or first_index < 0
    ):
        raise CertifierError("numeric first_index must be a nonnegative integer")
    if not isinstance(count, int) or isinstance(count, bool) or count < 10:
        raise CertifierError("numeric namespace count must be at least 10")
    names = [
        template.format(index=index) for index in range(first_index, first_index + count)
    ]
    if names == sorted(names):
        raise CertifierError(
            "numeric namespace fixture must cross a lexical-versus-numeric order boundary"
        )
    return names


def _numeric_namespace_relative_root(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise CertifierError(f"{label} must be nonempty")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise CertifierError(f"{label} escapes its mount")
    return path.as_posix()


def numeric_namespace_instances(contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand one direct or identity-templated numeric namespace contract."""

    entry_kind = contract.get("entry_kind")
    if entry_kind not in {"file", "directory"}:
        raise CertifierError("numeric entry_kind must be file or directory")
    has_relative = "relative_root" in contract
    has_template = "root_template" in contract
    if has_relative == has_template:
        raise CertifierError(
            "numeric namespace must declare exactly one of relative_root or root_template"
        )
    if has_relative:
        if "identities" in contract:
            raise CertifierError(
                "numeric relative_root namespace must not declare identities"
            )
        return [
            {
                "identity": None,
                "relative_root": _numeric_namespace_relative_root(
                    contract.get("relative_root"), "numeric relative_root"
                ),
            }
        ]

    template = contract.get("root_template")
    if not isinstance(template, str) or template.count("{identity}") != 1:
        raise CertifierError(
            "numeric root_template must contain {identity} exactly once"
        )
    remainder = template.replace("{identity}", "")
    if "{" in remainder or "}" in remainder:
        raise CertifierError("numeric root_template may contain no other format fields")
    identities = contract.get("identities")
    if (
        not isinstance(identities, list)
        or not identities
        or any(not isinstance(value, str) or not value for value in identities)
    ):
        raise CertifierError(
            "numeric identity-expanded namespace identities must be a nonempty string list"
        )
    if len(identities) != len(set(identities)):
        raise CertifierError(
            "numeric identity-expanded namespace identities must be unique"
        )
    instances = []
    for identity in identities:
        if (
            identity in {".", ".."}
            or "/" in identity
            or "\\" in identity
            or "{" in identity
            or "}" in identity
        ):
            raise CertifierError(f"numeric namespace identity is path-unsafe: {identity!r}")
        expanded = template.format(identity=identity)
        instances.append(
            {
                "identity": identity,
                "relative_root": _numeric_namespace_relative_root(
                    expanded, "expanded numeric root_template"
                ),
            }
        )
    expanded_roots = [item["relative_root"] for item in instances]
    if len(expanded_roots) != len(set(expanded_roots)):
        raise CertifierError("numeric root_template expansion produced duplicate roots")
    return instances


def numeric_namespace_contract_receipt(contract: dict[str, Any]) -> dict[str, Any]:
    """Return the exact normalized contract that every Step0 receipt must bind."""

    expected_names = numeric_namespace_expected_names(contract)
    instances = numeric_namespace_instances(contract)
    normalized = {
        "id": contract.get("id"),
        "entry_kind": contract.get("entry_kind"),
        "filename_template": contract.get("filename_template"),
        "first_index": contract.get("first_index"),
        "count": contract.get("count"),
        "instances": instances,
    }
    return {
        "contract_sha256": sha256_bytes(canonical_json(normalized)),
        "entry_kind": contract["entry_kind"],
        "count": len(expected_names),
        "instances": [
            {
                "identity": instance["identity"],
                "relative_root": instance["relative_root"],
                "count": len(expected_names),
                "ordered_names": expected_names,
            }
            for instance in instances
        ],
    }


def _within_materialized_root(path: str, remote_roots: list[str]) -> bool:
    if not path.startswith("/"):
        return False
    normalized = os.path.normpath(path)
    for root in remote_roots:
        normalized_root = os.path.normpath(root)
        try:
            if os.path.commonpath([normalized, normalized_root]) == normalized_root:
                return True
        except ValueError:
            continue
    return False


def _control_host_paths(value: str) -> list[str]:
    paths = [match.group(0).rstrip(",;)]}") for pattern in CONTROL_HOST_PATH_PATTERNS for match in pattern.finditer(value)]
    if value.startswith("~"):
        paths.append(value)
    return paths


def validate_profile_host_path_provenance(
    profile: dict[str, Any], remote_roots: list[str]
) -> tuple[list[str], dict[str, Any]]:
    """Reject control-host commands/interpreters before any simulation can run."""

    failures: list[str] = []
    checked: list[str] = []

    def check_value(label: str, value: str, *, interpreter: bool) -> None:
        checked.append(label)
        for candidate in _control_host_paths(value):
            if not _within_materialized_root(candidate, remote_roots):
                failures.append(
                    f"{label} contains control-host absolute path without materialized-root provenance: "
                    f"{candidate}"
                )
        if not interpreter:
            return
        if value == "{python}":
            return
        if value.startswith("{mount:") and "}" in value:
            return
        if "{" in value or "}" in value:
            failures.append(
                f"{label} must use {{python}} or one declared mount placeholder"
            )
            return
        is_drive = re.match(r"^[A-Za-z]:[\\/]", value) is not None
        if not os.path.isabs(value) and not is_drive:
            failures.append(
                f"{label} must use {{python}} or an absolute target-resolved interpreter"
            )

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                label = f"{path}.{key}" if path else str(key)
                lowered = str(key).lower()
                if lowered == "command":
                    tokens = child if isinstance(child, list) else [child]
                    for index, token in enumerate(tokens):
                        if isinstance(token, str):
                            check_value(
                                f"{label}[{index}]",
                                token,
                                interpreter=index == 0,
                            )
                    continue
                if (
                    lowered in {"executable", "interpreter"}
                    or lowered.endswith("_executable")
                    or lowered.endswith("_interpreter")
                ) and isinstance(child, str):
                    check_value(label, child, interpreter=True)
                    continue
                visit(child, label)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(profile, "")
    return failures, {
        "status": "PASS" if not failures else "FAIL",
        "checked_fields": checked,
        "materialized_remote_roots": sorted(remote_roots),
    }


def resolve_python_executable(value: Any, label: str) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    raw = sys.executable if value == "{python}" else value
    if "{" in raw or "}" in raw:
        return None
    path = Path(raw).expanduser().resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        return None
    return path


def iter_numeric_namespace_contracts(
    profile: dict[str, Any],
) -> Iterable[tuple[dict[str, Any], dict[str, Any]]]:
    for mount in profile.get("mounts", []):
        if not isinstance(mount, dict):
            continue
        for contract in mount.get("numeric_indexed_namespaces", []):
            if isinstance(contract, dict):
                yield mount, contract


def validate_step0_run(
    *,
    working: Path,
    stdout: str,
    profile: dict[str, Any],
    expect_heavy: bool,
) -> tuple[list[str], dict[str, Any], bool]:
    """Validate the authenticated Step0 receipt and its position before heavy work."""

    failures: list[str] = []
    evidence: dict[str, Any] = {}
    step0 = profile["kernel"]["step0"]
    receipt_path = safe_output_path(working, step0["receipt_path"])
    receipt_present = receipt_path.is_file()
    evidence["receipt_path"] = step0["receipt_path"]
    evidence["receipt_present"] = receipt_present
    if not receipt_present:
        return ["Step0 deterministic-invariant receipt is missing"], evidence, False
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Step0 deterministic-invariant receipt is malformed: {exc}"], evidence, True
    if not isinstance(receipt, dict):
        return ["Step0 deterministic-invariant receipt must be an object"], evidence, True
    if receipt.get("status") != "PASS":
        failures.append("Step0 deterministic-invariant receipt status is not PASS")
    expected_invariants = step0["deterministic_invariants"]
    if receipt.get("invariants") != expected_invariants:
        failures.append("Step0 receipt does not bind the exact ordered invariant inventory")

    expected_namespaces: dict[str, Any] = {}
    observed_namespaces = receipt.get("numeric_namespaces")
    if not isinstance(observed_namespaces, dict):
        failures.append("Step0 receipt numeric_namespaces must be an object")
        observed_namespaces = {}
    for _mount, contract in iter_numeric_namespace_contracts(profile):
        namespace_id = contract["id"]
        expected_record = numeric_namespace_contract_receipt(contract)
        record = observed_namespaces.get(namespace_id)
        expected_namespaces[namespace_id] = {
            "contract_sha256": expected_record["contract_sha256"],
            "entry_kind": expected_record["entry_kind"],
            "count": expected_record["count"],
            "instance_count": len(expected_record["instances"]),
            "instances_sha256": sha256_bytes(
                canonical_json(expected_record["instances"])
            ),
        }
        if not isinstance(record, dict):
            failures.append(f"Step0 receipt lacks numeric namespace {namespace_id!r}")
            continue
        if record.get("contract_sha256") != expected_record["contract_sha256"]:
            failures.append(
                f"Step0 numeric namespace {namespace_id!r} contract binding drift"
            )
        if record.get("entry_kind") != expected_record["entry_kind"]:
            failures.append(
                f"Step0 numeric namespace {namespace_id!r} entry-kind drift"
            )
        if record.get("count") != expected_record["count"]:
            failures.append(f"Step0 numeric namespace {namespace_id!r} cardinality drift")
        if record.get("instances") != expected_record["instances"]:
            failures.append(
                f"Step0 numeric namespace {namespace_id!r} expanded-root or numeric-order drift"
            )
    declared_ids = {contract["id"] for _, contract in iter_numeric_namespace_contracts(profile)}
    if set(observed_namespaces) != declared_ids:
        failures.append("Step0 receipt numeric namespace inventory drift")

    completion_marker = step0["completion_marker"]
    heavy_marker = step0["heavy_work_marker"]
    completion_positions = [
        match.start() for match in re.finditer(re.escape(completion_marker), stdout)
    ]
    heavy_positions = [match.start() for match in re.finditer(re.escape(heavy_marker), stdout)]
    evidence.update(
        {
            "status": receipt.get("status"),
            "invariants": receipt.get("invariants"),
            "numeric_namespaces": expected_namespaces,
            "completion_marker_positions": completion_positions,
            "heavy_work_marker_positions": heavy_positions,
        }
    )
    if len(completion_positions) != 1:
        failures.append("Step0 completion marker must be emitted exactly once")
    if expect_heavy:
        if len(heavy_positions) != 1:
            failures.append("heavy-work marker must be emitted exactly once")
        if (
            len(completion_positions) == 1
            and len(heavy_positions) == 1
            and completion_positions[0] >= heavy_positions[0]
        ):
            failures.append("Step0 deterministic gates did not complete before heavy work")
    elif heavy_positions:
        failures.append("Step0-only preheavy probe reached heavy work")
    return failures, evidence, True


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CertifierError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CertifierError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve(base: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (base / path).resolve()


def derive_provider_sources(metadata: dict[str, Any]) -> tuple[list[str], list[dict[str, str]]]:
    """Derive canonical Kaggle input roots from provider-owned metadata only."""

    failures: list[str] = []
    sources: list[dict[str, str]] = []
    specifications = (
        (
            "dataset_sources",
            "dataset",
            re.compile(r"^[a-z0-9][a-z0-9_-]*/[a-z0-9][a-z0-9_-]*$"),
            "/kaggle/input/datasets/{source_id}",
        ),
        (
            "competition_sources",
            "competition",
            re.compile(r"^[a-z0-9][a-z0-9_-]*$"),
            "/kaggle/input/competitions/{source_id}",
        ),
    )
    seen: set[tuple[str, str]] = set()
    for metadata_key, source_type, pattern, root_template in specifications:
        values = metadata.get(metadata_key, [])
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            failures.append(f"metadata {metadata_key} must be a list of provider IDs")
            continue
        for source_id in values:
            if not pattern.fullmatch(source_id):
                failures.append(f"metadata {metadata_key} has malformed provider ID: {source_id!r}")
                continue
            key = (source_type, source_id)
            if key in seen:
                failures.append(f"metadata {metadata_key} repeats provider ID: {source_id}")
                continue
            seen.add(key)
            sources.append(
                {
                    "source_type": source_type,
                    "source_id": source_id,
                    "canonical_root": root_template.format(source_id=source_id),
                }
            )
    return failures, sources


def validate_provider_layout(
    *,
    label: str,
    mount: dict[str, Any],
    local_root: Path,
    remote_root: str,
    project_root: Path,
    provider_source: dict[str, str] | None,
) -> tuple[list[str], dict[str, Any] | None]:
    """Bind a simulated mount to the provider's downloaded path topology."""

    failures: list[str] = []
    layout = mount.get("provider_layout")
    if layout is None:
        failures.append(f"{label}.provider_layout is required for every release asset mount")
        return failures, None
    if not isinstance(layout, dict):
        return [f"{label}.provider_layout must be an object"], None

    source_type = layout.get("source_type")
    source_id = layout.get("source_id")
    if provider_source is None:
        failures.append(f"{label} provider source is not declared by kernel metadata")
        canonical_root = None
    else:
        canonical_root = provider_source["canonical_root"]
        if source_type != provider_source["source_type"] or source_id != provider_source["source_id"]:
            failures.append(f"{label} provider provenance does not match kernel metadata")
    if source_type not in {"dataset", "competition"}:
        failures.append(f"{label}.provider_layout.source_type must be dataset or competition")
    if not isinstance(source_id, str) or not source_id:
        failures.append(f"{label}.provider_layout.source_id must be nonempty")

    # Competition inputs are provider-mounted raw data rather than release
    # carriers, so their topology is authenticated by the independently
    # derived metadata root. Dataset carriers additionally require a
    # byte-perfect provider round trip.
    if source_type == "competition":
        if canonical_root is not None and remote_root != canonical_root:
            failures.append(f"{label} remote_root does not equal metadata-derived canonical root")
        return failures, {
            "source_type": source_type,
            "source_id": source_id,
            "effective_remote_root": canonical_root,
            "roundtrip_receipt": None,
            "mount_layout_correction": None,
        }

    receipt_ref = layout.get("roundtrip_receipt")
    if not isinstance(receipt_ref, dict):
        return [f"{label}.provider_layout.roundtrip_receipt must be an object"], None
    receipt_path_raw = receipt_ref.get("path")
    receipt_sha = receipt_ref.get("sha256")
    if not isinstance(receipt_path_raw, str) or not receipt_path_raw:
        return [f"{label} provider roundtrip receipt path is missing"], None
    if not isinstance(receipt_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", receipt_sha):
        return [f"{label} provider roundtrip receipt SHA-256 is malformed"], None
    receipt_path = resolve(project_root, receipt_path_raw)
    if not receipt_path.is_file():
        return [f"{label} provider roundtrip receipt is missing: {receipt_path}"], None
    if sha256_file(receipt_path) != receipt_sha:
        return [f"{label} provider roundtrip receipt SHA-256 drift"], None
    try:
        receipt = load_json(receipt_path)
    except CertifierError as exc:
        return [f"{label} provider roundtrip receipt is invalid: {exc}"], None
    if receipt.get("status") != "PASS":
        failures.append(f"{label} provider roundtrip receipt is not PASS")
    if receipt.get("dataset_id") != source_id:
        failures.append(f"{label} provider roundtrip dataset_id does not match metadata source")
    comparison = receipt.get("comparison")
    expected_comparison = {
        "same_declared_paths": True,
        "same_declared_bytes": True,
        "same_declared_sha256": True,
        "raw_or_score_payload_present": False,
    }
    if not isinstance(comparison, dict) or any(
        comparison.get(key) is not value for key, value in expected_comparison.items()
    ):
        failures.append(f"{label} provider roundtrip comparison is not byte/path exact")
    download_root_raw = receipt.get("download_root", receipt.get("downloaded_root"))
    if not isinstance(download_root_raw, str) or not download_root_raw:
        failures.append(f"{label} provider roundtrip download root is missing")
        download_root = None
    else:
        download_root = resolve(project_root, download_root_raw)
        if download_root.resolve() != local_root.resolve():
            failures.append(
                f"{label} local_root is not the exact provider roundtrip download root"
            )

    effective_remote = receipt.get("expected_mount_root")
    correction_summary = None
    correction_ref = layout.get("mount_layout_correction")
    if correction_ref is not None:
        if not isinstance(correction_ref, dict):
            failures.append(f"{label}.provider_layout.mount_layout_correction must be an object")
        else:
            correction_path_raw = correction_ref.get("path")
            correction_sha = correction_ref.get("sha256")
            if not isinstance(correction_path_raw, str) or not correction_path_raw:
                failures.append(f"{label} mount-layout correction path is missing")
            elif not isinstance(correction_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", correction_sha):
                failures.append(f"{label} mount-layout correction SHA-256 is malformed")
            else:
                correction_path = resolve(project_root, correction_path_raw)
                if not correction_path.is_file():
                    failures.append(f"{label} mount-layout correction is missing: {correction_path}")
                elif sha256_file(correction_path) != correction_sha:
                    failures.append(f"{label} mount-layout correction SHA-256 drift")
                else:
                    correction = load_json(correction_path)
                    if not str(correction.get("status", "")).startswith("PASS_"):
                        failures.append(f"{label} mount-layout correction is not PASS")
                    superseded = correction.get("superseded_roundtrip_receipt")
                    if not isinstance(superseded, dict) or superseded.get("sha256") != receipt_sha:
                        failures.append(
                            f"{label} mount-layout correction does not bind the roundtrip receipt"
                        )
                    effective_remote = correction.get("correct_expected_mount_root")
                    correction_summary = {
                        "path": str(correction_path),
                        "sha256": correction_sha,
                    }
    if effective_remote != canonical_root:
        failures.append(
            f"{label} provider receipt root does not equal metadata-derived canonical root"
        )
    if canonical_root is not None and remote_root != canonical_root:
        failures.append(f"{label} remote_root does not equal metadata-derived canonical root")
    summary = {
        "source_type": source_type,
        "source_id": source_id,
        "roundtrip_receipt": {"path": str(receipt_path), "sha256": receipt_sha},
        "dataset_id": receipt.get("dataset_id"),
        "dataset_version": receipt.get("dataset_version"),
        "download_root": None if download_root is None else str(download_root),
        "effective_remote_root": effective_remote,
        "mount_layout_correction": correction_summary,
    }
    return failures, summary


def load_lmt_policy(path: Path) -> dict[str, Any]:
    try:
        source = path.read_text(encoding="utf-8")
        block = source.split(LMT_POLICY_BEGIN, 1)[1].split(LMT_POLICY_END, 1)[0].strip()
        if block.startswith("```json"):
            block = block[len("```json") :].strip()
        if block.endswith("```"):
            block = block[:-3].strip()
        policy = json.loads(block)
    except (OSError, IndexError, json.JSONDecodeError) as exc:
        raise CertifierError(f"LMT policy is absent or malformed: {exc}") from exc
    if not isinstance(policy, dict) or policy.get("schema") != "cell-tracking.autonomy-limits.v1":
        raise CertifierError("LMT policy schema mismatch")
    kaggle = policy.get("kaggle")
    if not isinstance(kaggle, dict):
        raise CertifierError("LMT Kaggle policy is missing")
    cap = kaggle.get("autonomous_projection_strictly_below_hours")
    if not isinstance(cap, (int, float)) or isinstance(cap, bool) or not math.isfinite(float(cap)) or cap <= 0:
        raise CertifierError("LMT autonomous Kaggle projection cap must be finite and positive")
    if kaggle.get("auto_approved_wall_clock_kill_seconds") is not None:
        raise CertifierError("LMT auto-approved Kaggle runs must not have an agent wall-clock kill")
    return policy


def find_lmt(start: Path) -> Path:
    resolved = start.resolve()
    for directory in (resolved, *resolved.parents):
        candidate = directory / "LMT.md"
        if candidate.is_file():
            load_lmt_policy(candidate)
            return candidate
    raise CertifierError(f"no LMT.md found above {resolved}")


def profile_lmt(profile_path: Path, profile: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    value = profile.get("limits_file")
    if not isinstance(value, str) or not value:
        raise CertifierError("profile limits_file must bind repository LMT.md")
    path = resolve(profile_path.parent.resolve(), value)
    if path.name != "LMT.md":
        raise CertifierError("limits_file must resolve to LMT.md")
    return path, load_lmt_policy(path)


def title_slug(title: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", title.lower())).strip("-")


def percentile(values: Iterable[float], probability: float) -> float:
    ordered = sorted(float(v) for v in values)
    if not ordered:
        raise CertifierError("percentile of empty collection")
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def source_text(entrypoint: Path) -> str:
    if entrypoint.suffix == ".py":
        return entrypoint.read_text(encoding="utf-8")
    if entrypoint.suffix == ".ipynb":
        notebook = load_json(entrypoint)
        chunks: list[str] = []
        for cell in notebook.get("cells", []):
            if isinstance(cell, dict) and cell.get("cell_type") == "code":
                source = cell.get("source", [])
                chunks.append("".join(source) if isinstance(source, list) else str(source))
        return "\n\n".join(chunks)
    raise CertifierError("entrypoint must be .py or .ipynb")


def imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def exact_subset(observed: Any, expected: Any, prefix: str = "metadata") -> list[str]:
    failures: list[str] = []
    if not isinstance(expected, dict) or not isinstance(observed, dict):
        return [f"{prefix}: exact-subset operands must be objects"]
    for key, wanted in expected.items():
        if key not in observed:
            failures.append(f"{prefix}.{key}: missing")
        elif observed[key] != wanted:
            failures.append(f"{prefix}.{key}: expected {wanted!r}, observed {observed[key]!r}")
    return failures


def _required_number(obj: dict[str, Any], key: str, failures: list[str], *, positive: bool = True) -> float:
    value = obj.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        failures.append(f"{key} must be numeric")
        return 0.0
    number = float(value)
    if not math.isfinite(number) or (positive and number <= 0):
        failures.append(f"{key} must be finite" + (" and positive" if positive else ""))
    return number


def _subprocess_calls(tree: ast.AST) -> set[str]:
    """Return subprocess APIs reached syntactically anywhere in an entrypoint."""

    calls: set[str] = set()
    module_aliases = {"subprocess"}
    direct_aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "subprocess":
                    module_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "subprocess":
            for alias in node.names:
                direct_aliases[alias.asname or alias.name] = alias.name
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if (
            isinstance(function, ast.Attribute)
            and isinstance(function.value, ast.Name)
            and function.value.id in module_aliases
        ):
            calls.add(function.attr)
        elif isinstance(function, ast.Name) and function.id in direct_aliases:
            calls.add(direct_aliases[function.id])
    return calls


def _dynamic_exec_calls(tree: ast.AST) -> int:
    """Count executable dynamic-source boundaries in the transmitted entrypoint."""

    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "exec"
    )


def _top_level_defined_symbols(tree: ast.AST) -> set[str]:
    """Return names that the transmitted outer module defines at top level."""

    names: set[str] = set()
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.Import):
            names.update(alias.asname or alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.asname or alias.name for alias in node.names)
    return names


def _probe_python_version(executable: Path) -> tuple[str | None, str | None]:
    """Return the exact interpreter version or a bounded diagnostic."""

    try:
        completed = subprocess.run(
            [str(executable), "-c", "import platform; print(platform.python_version())"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"target Python probe failed: {type(exc).__name__}: {exc}"
    version = completed.stdout.strip()
    if completed.returncode != 0 or not version:
        tail = completed.stderr.strip()[-500:]
        return None, f"target Python probe returned {completed.returncode}: {tail}"
    return version, None


def _validate_probe_shape(label: str, probe: Any, source: str) -> list[str]:
    failures: list[str] = []
    if not isinstance(probe, dict):
        return [f"{label} must be an object"]
    timeout = probe.get("timeout_seconds")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        failures.append(f"{label}.timeout_seconds must be a positive integer")
    env = probe.get("env")
    if not isinstance(env, dict) or not env or any(
        not isinstance(key, str) or not key or not isinstance(value, str)
        for key, value in env.items()
    ):
        failures.append(f"{label}.env must be a nonempty string mapping")
        env = {}
    for key in env:
        if key not in source:
            failures.append(f"{label} environment control is absent from source: {key}")
    codes = probe.get("exit_codes", [0])
    if not isinstance(codes, list) or not codes or any(
        not isinstance(code, int) or isinstance(code, bool) for code in codes
    ):
        failures.append(f"{label}.exit_codes must be a nonempty integer list")
    markers = probe.get("stdout_markers")
    if not isinstance(markers, list) or not markers or any(
        not isinstance(marker, str) or not marker for marker in markers
    ):
        failures.append(f"{label}.stdout_markers must be a nonempty string list")
    else:
        for marker in markers:
            if marker not in source:
                failures.append(f"{label} stdout marker is absent from source: {marker}")
    outputs = probe.get("required_outputs")
    if not isinstance(outputs, list) or not outputs:
        failures.append(f"{label}.required_outputs must be nonempty")
        outputs = []
    paths: set[str] = set()
    for index, output in enumerate(outputs):
        output_label = f"{label}.required_outputs[{index}]"
        if not isinstance(output, dict) or not isinstance(output.get("path"), str):
            failures.append(f"{output_label} is malformed")
            continue
        path = output["path"]
        try:
            safe_output_path(Path("/probe"), path)
        except CertifierError as exc:
            failures.append(f"{output_label}: {exc}")
        if path in paths:
            failures.append(f"{label} repeats required output path: {path}")
        paths.add(path)
        if output.get("kind", "file") not in ALLOWED_KINDS:
            failures.append(f"{output_label} has unsupported kind")
        if output.get("repeatability", "none") not in {"byte", "none"}:
            failures.append(f"{output_label} repeatability must be 'byte' or 'none'")
        if path.lower().endswith(".mp4") and output.get("kind") != "mp4":
            failures.append(f"{output_label} promises MP4 bytes but kind is not 'mp4'")
    completion = probe.get("completion")
    if not isinstance(completion, dict):
        failures.append(f"{label}.completion must be an object")
    else:
        if completion.get("path") not in paths:
            failures.append(f"{label}.completion.path must be a required output")
        for key in ("status_pointer", "units_pointer"):
            if not isinstance(completion.get(key), str):
                failures.append(f"{label}.completion.{key} missing")
        if not isinstance(completion.get("success_values"), list) or not completion.get(
            "success_values"
        ):
            failures.append(f"{label}.completion.success_values must be nonempty")
    return failures


def _normalise_safety_probe(name: str, probe: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    scenario = copy.deepcopy(probe)
    scenario.update(
        {
            "name": f"runtime_safety::{name}",
            "role": "runtime_safety",
            "workload_units": 1,
            "repeats": 1,
            "_runtime_safety_contract": contract,
        }
    )
    return scenario


def validate_runtime_safety_contract(
    runtime_safety: Any,
    *,
    source: str,
    tree: ast.AST,
    mount_names: set[str],
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
    """Validate target-like probes for release subprocess, linker, diagnostics and media paths."""

    failures: list[str] = []
    probes: list[dict[str, Any]] = []
    subprocess_apis = _subprocess_calls(tree)
    has_subprocess = bool(subprocess_apis & {"Popen", "run", "call", "check_call", "check_output"})
    string_literals = {
        node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    has_proc_rss_monitor = has_subprocess and (
        "VmRSS" in source or any(value == "/proc" or value.startswith("/proc/") for value in string_literals)
    )
    linker_variables = sorted(variable for variable in LINKER_ENVIRONMENT_VARIABLES if variable in source)
    has_media = ".mp4" in source.lower() or "VideoWriter" in source or "videowriter" in source
    dynamic_exec_calls = _dynamic_exec_calls(tree)
    has_dependency_reexec = (
        "os.execve" in source
        and "Path(__file__).resolve()" in source
    )
    detected = {
        "subprocess_apis": sorted(subprocess_apis),
        "proc_rss_monitor": has_proc_rss_monitor,
        "linker_variables": linker_variables,
        "media_encode_or_path": has_media,
        "dynamic_exec_calls": dynamic_exec_calls,
        "dependency_reexec_from_file": has_dependency_reexec,
    }
    if not isinstance(runtime_safety, dict):
        return ["runtime_safety must be an object"], probes, detected

    post_tail = runtime_safety.get("post_heavy_tail")
    if not isinstance(post_tail, dict):
        failures.append("runtime_safety.post_heavy_tail must be an object")
    else:
        if post_tail.get("mode") != "exact_outer_entrypoint_probe":
            failures.append(
                "runtime_safety.post_heavy_tail.mode must be exact_outer_entrypoint_probe"
            )
        entrypoint_marker = post_tail.get("entrypoint_marker")
        completion_marker = post_tail.get("completion_marker")
        for key, marker in (
            ("entrypoint_marker", entrypoint_marker),
            ("completion_marker", completion_marker),
        ):
            if not isinstance(marker, str) or not marker:
                failures.append(f"runtime_safety.post_heavy_tail.{key} must be nonempty")
            elif marker not in source:
                failures.append(
                    f"runtime_safety.post_heavy_tail.{key} is absent from the entrypoint"
                )
        required_symbols = post_tail.get("required_symbols")
        if not isinstance(required_symbols, list) or not required_symbols or any(
            not isinstance(name, str) or not name for name in required_symbols
        ):
            failures.append(
                "runtime_safety.post_heavy_tail.required_symbols must be a nonempty string list"
            )
            required_symbols = []
        elif len(required_symbols) != len(set(required_symbols)):
            failures.append(
                "runtime_safety.post_heavy_tail.required_symbols must be unique"
            )
        missing_symbols = sorted(
            set(required_symbols) - _top_level_defined_symbols(tree)
        )
        if missing_symbols:
            failures.append(
                "post-heavy outer symbols are not top-level-defined in the transmitted script: "
                f"{missing_symbols}"
            )
        executable_raw = post_tail.get("python_executable")
        version_prefix = post_tail.get("python_version_prefix")
        executable: Path | None = None
        if not isinstance(executable_raw, str) or not executable_raw:
            failures.append(
                "runtime_safety.post_heavy_tail.python_executable is required"
            )
        else:
            executable = resolve_python_executable(
                executable_raw,
                "runtime_safety.post_heavy_tail.python_executable",
            )
            if executable is None:
                failures.append(
                    "runtime_safety.post_heavy_tail.python_executable must be {python} "
                    "or an executable target-resolved path"
                )
        if not isinstance(version_prefix, str) or not re.fullmatch(r"\d+\.\d+", version_prefix):
            failures.append(
                "runtime_safety.post_heavy_tail.python_version_prefix must be major.minor"
            )
        elif executable is not None:
            observed_version, version_error = _probe_python_version(executable)
            if version_error is not None:
                failures.append(version_error)
            elif observed_version is None or not observed_version.startswith(version_prefix + "."):
                failures.append(
                    "post-heavy-tail target Python version mismatch: "
                    f"required {version_prefix}, observed {observed_version}"
                )
        probe = post_tail.get("probe")
        failures.extend(
            _validate_probe_shape("runtime_safety.post_heavy_tail.probe", probe, source)
        )
        receipt_path = post_tail.get("receipt_path")
        if not isinstance(receipt_path, str) or not receipt_path:
            failures.append("runtime_safety.post_heavy_tail.receipt_path is required")
        elif (
            isinstance(probe, dict)
            and executable is not None
            and isinstance(version_prefix, str)
        ):
            scenario = _normalise_safety_probe(
                "exact_outer_post_heavy_tail",
                probe,
                {
                    "kind": "post_heavy_tail",
                    "receipt_path": receipt_path,
                    "python_version_prefix": version_prefix,
                    "entrypoint_marker": entrypoint_marker,
                    "completion_marker": completion_marker,
                    "required_symbols": list(required_symbols),
                },
            )
            scenario["_python_executable"] = str(executable)
            probes.append(scenario)

    dynamic = runtime_safety.get("dynamic_module_execution")
    if not isinstance(dynamic, dict):
        failures.append("runtime_safety.dynamic_module_execution must be an object")
    else:
        mode = dynamic.get("mode")
        if dynamic_exec_calls:
            if mode != "registered_target_minor_probe":
                failures.append(
                    "dynamic exec requires dynamic_module_execution.mode=registered_target_minor_probe"
                )
            module_names = dynamic.get("registered_module_names")
            if not isinstance(module_names, list) or not module_names or any(
                not isinstance(name, str) or not name for name in module_names
            ):
                failures.append(
                    "runtime_safety.dynamic_module_execution.registered_module_names "
                    "must be a nonempty string list"
                )
                module_names = []
            elif len(module_names) != len(set(module_names)):
                failures.append(
                    "runtime_safety.dynamic_module_execution.registered_module_names "
                    "must be unique"
                )
            for name in module_names:
                if name not in source:
                    failures.append(f"registered dynamic module name is absent from source: {name}")
            if "sys.modules" not in source or "ModuleType" not in source:
                failures.append(
                    "dynamic exec source must register a real ModuleType in sys.modules"
                )
            executable_raw = dynamic.get("python_executable")
            version_prefix = dynamic.get("python_version_prefix")
            executable: Path | None = None
            if not isinstance(executable_raw, str) or not executable_raw:
                failures.append(
                    "runtime_safety.dynamic_module_execution.python_executable is required"
                )
            else:
                executable = resolve_python_executable(
                    executable_raw,
                    "runtime_safety.dynamic_module_execution.python_executable",
                )
                if executable is None:
                    failures.append(
                        "runtime_safety.dynamic_module_execution.python_executable "
                        "must be {python} or an executable target-resolved path"
                    )
            if not isinstance(version_prefix, str) or not re.fullmatch(r"\d+\.\d+", version_prefix):
                failures.append(
                    "runtime_safety.dynamic_module_execution.python_version_prefix "
                    "must be a major.minor string"
                )
            elif executable is not None:
                observed_version, version_error = _probe_python_version(executable)
                if version_error is not None:
                    failures.append(version_error)
                elif observed_version is None or not observed_version.startswith(version_prefix + "."):
                    failures.append(
                        "dynamic module target Python version mismatch: "
                        f"required {version_prefix}, observed {observed_version}"
                    )
            probe = dynamic.get("probe")
            failures.extend(
                _validate_probe_shape(
                    "runtime_safety.dynamic_module_execution.probe", probe, source
                )
            )
            receipt_path = dynamic.get("receipt_path")
            if not isinstance(receipt_path, str) or not receipt_path:
                failures.append(
                    "runtime_safety.dynamic_module_execution.receipt_path is required"
                )
            elif (
                isinstance(probe, dict)
                and executable is not None
                and isinstance(version_prefix, str)
            ):
                scenario = _normalise_safety_probe(
                    "registered_target_minor_dynamic_module",
                    probe,
                    {
                        "kind": "dynamic_module_execution",
                        "receipt_path": receipt_path,
                        "python_version_prefix": version_prefix,
                        "registered_module_names": list(module_names),
                    },
                )
                scenario["_python_executable"] = str(executable)
                probes.append(scenario)
            lifecycle = dynamic.get("reexec_lifecycle")
            if has_dependency_reexec:
                if not isinstance(lifecycle, dict):
                    failures.append(
                        "dynamic source re-executes Path(__file__) but has no reexec_lifecycle contract"
                    )
                else:
                    if lifecycle.get("mode") != "outer_saved_script_reentry_probe":
                        failures.append(
                            "dynamic re-exec requires reexec_lifecycle.mode="
                            "outer_saved_script_reentry_probe"
                        )
                    reexec_module_name = lifecycle.get("reexec_module_name")
                    if reexec_module_name not in module_names:
                        failures.append(
                            "reexec_lifecycle.reexec_module_name must name a registered dynamic module"
                        )
                    entrypoint_marker = lifecycle.get("entrypoint_marker")
                    if not isinstance(entrypoint_marker, str) or not entrypoint_marker:
                        failures.append(
                            "reexec_lifecycle.entrypoint_marker must be nonempty"
                        )
                    elif entrypoint_marker not in source:
                        failures.append(
                            "reexec lifecycle entrypoint marker is absent from kernel source"
                        )
                    lifecycle_probe = lifecycle.get("probe")
                    failures.extend(
                        _validate_probe_shape(
                            "runtime_safety.dynamic_module_execution.reexec_lifecycle.probe",
                            lifecycle_probe,
                            source,
                        )
                    )
                    lifecycle_receipt = lifecycle.get("receipt_path")
                    if not isinstance(lifecycle_receipt, str) or not lifecycle_receipt:
                        failures.append(
                            "reexec_lifecycle.receipt_path must be nonempty"
                        )
                    elif (
                        isinstance(lifecycle_probe, dict)
                        and executable is not None
                        and isinstance(version_prefix, str)
                    ):
                        lifecycle_scenario = _normalise_safety_probe(
                            "outer_saved_script_reentry",
                            lifecycle_probe,
                            {
                                "kind": "dependency_reexec_lifecycle",
                                "receipt_path": lifecycle_receipt,
                                "python_version_prefix": version_prefix,
                                "entrypoint_marker": entrypoint_marker,
                                "reexec_module_name": reexec_module_name,
                            },
                        )
                        lifecycle_scenario["_python_executable"] = str(executable)
                        probes.append(lifecycle_scenario)
            elif lifecycle is not None:
                failures.append(
                    "reexec_lifecycle must be absent when no Path(__file__) execve is detected"
                )
        elif mode != "not_applicable":
            failures.append(
                "runtime_safety.dynamic_module_execution.mode must be not_applicable "
                "when no dynamic exec is detected"
            )

    monitor = runtime_safety.get("subprocess_monitor")
    if not isinstance(monitor, dict):
        failures.append("runtime_safety.subprocess_monitor must be an object")
    else:
        mode = monitor.get("mode")
        if has_proc_rss_monitor:
            if mode != "exit_reap_aware":
                failures.append(
                    "a /proc/VmRSS subprocess monitor requires subprocess_monitor.mode=exit_reap_aware"
                )
            probe = monitor.get("probe")
            failures.extend(_validate_probe_shape("runtime_safety.subprocess_monitor.probe", probe, source))
            receipt_path = monitor.get("receipt_path")
            if not isinstance(receipt_path, str) or not receipt_path:
                failures.append("runtime_safety.subprocess_monitor.receipt_path is required")
            elif isinstance(probe, dict):
                probes.append(
                    _normalise_safety_probe(
                        "subprocess_monitor_exit_between_polls",
                        probe,
                        {"kind": "subprocess_monitor", "receipt_path": receipt_path},
                    )
                )
        elif mode != "not_applicable":
            failures.append(
                "runtime_safety.subprocess_monitor.mode must be not_applicable when no /proc RSS monitor is detected"
            )

    linker = runtime_safety.get("release_linker_environment")
    if not isinstance(linker, dict):
        failures.append("runtime_safety.release_linker_environment must be an object")
    else:
        mode = linker.get("mode")
        if linker_variables:
            if mode not in {"reconstructed", "target_like_probe"}:
                failures.append(
                    "release linker environment requires mode reconstructed or target_like_probe"
                )
            variable = linker.get("inherited_variable")
            if variable != "LD_LIBRARY_PATH":
                failures.append(
                    "runtime_safety.release_linker_environment.inherited_variable must be LD_LIBRARY_PATH"
                )
            trusted_roots = linker.get("trusted_roots")
            if not isinstance(trusted_roots, list) or not trusted_roots:
                failures.append("runtime_safety.release_linker_environment.trusted_roots must be nonempty")
                trusted_roots = []
            observed_sources: set[str] = set()
            for index, root in enumerate(trusted_roots):
                label = f"runtime_safety.release_linker_environment.trusted_roots[{index}]"
                if not isinstance(root, dict):
                    failures.append(f"{label} must be an object")
                    continue
                path = root.get("path")
                source_kind = root.get("source")
                if source_kind not in {"authenticated_carrier", "allowlisted_host"}:
                    failures.append(f"{label}.source is not trusted")
                else:
                    observed_sources.add(source_kind)
                if not isinstance(path, str) or not path:
                    failures.append(f"{label}.path must be nonempty")
                    continue
                placeholders = re.findall(r"\{mount:([^}]+)\}", path)
                if placeholders:
                    if any(name not in mount_names for name in placeholders):
                        failures.append(f"{label}.path references an unknown mount")
                    if source_kind != "authenticated_carrier":
                        failures.append(f"{label} mount roots must be authenticated_carrier")
                elif not os.path.isabs(path) or os.path.normpath(path) != path:
                    failures.append(f"{label}.path must be normalized absolute or mount-bound")
            if "authenticated_carrier" not in observed_sources or "allowlisted_host" not in observed_sources:
                failures.append(
                    "linker trusted_roots must include authenticated_carrier and allowlisted_host provenance"
                )
            linker_probes = linker.get("probes")
            if not isinstance(linker_probes, list) or not linker_probes:
                failures.append("runtime_safety.release_linker_environment.probes must be nonempty")
                linker_probes = []
            observed_values: list[str] = []
            for index, item in enumerate(linker_probes):
                label = f"runtime_safety.release_linker_environment.probes[{index}]"
                failures.extend(_validate_probe_shape(label, item, source))
                if not isinstance(item, dict):
                    continue
                env = item.get("env", {})
                raw_value = env.get("LD_LIBRARY_PATH") if isinstance(env, dict) else None
                if not isinstance(raw_value, str):
                    failures.append(f"{label}.env must set LD_LIBRARY_PATH to an exact string")
                    continue
                observed_values.append(raw_value)
                receipt_path = item.get("receipt_path")
                if not isinstance(receipt_path, str) or not receipt_path:
                    failures.append(f"{label}.receipt_path is required")
                    continue
                probes.append(
                    _normalise_safety_probe(
                        f"release_linker_environment_{index}",
                        item,
                        {
                            "kind": "release_linker_environment",
                            "receipt_path": receipt_path,
                            "raw_value": raw_value,
                            "mode": mode,
                            "trusted_roots": trusted_roots,
                        },
                    )
                )
            has_exact_empty = "" in observed_values
            has_empty_component = any(
                value and any(component == "" for component in value.split(os.pathsep))
                for value in observed_values
            )
            has_relative_component = any(
                any(component and not os.path.isabs(component) for component in value.split(os.pathsep))
                for value in observed_values
            )
            if not has_exact_empty:
                failures.append("linker probes must include an exactly empty inherited LD_LIBRARY_PATH")
            if not has_empty_component:
                failures.append(
                    "linker probes must include a leading, trailing, or doubled empty path component"
                )
            if not has_relative_component:
                failures.append("linker probes must include an inherited relative path component")
        elif mode != "not_applicable":
            failures.append(
                "runtime_safety.release_linker_environment.mode must be not_applicable when no linker variable is detected"
            )

    diagnostics = runtime_safety.get("child_diagnostics")
    if not isinstance(diagnostics, dict):
        failures.append("runtime_safety.child_diagnostics must be an object")
    else:
        mode = diagnostics.get("mode")
        if has_subprocess:
            if mode != "durable_bounded":
                failures.append(
                    "release subprocesses require child_diagnostics.mode=durable_bounded"
                )
            max_capture = diagnostics.get("max_capture_bytes")
            if (
                not isinstance(max_capture, int)
                or isinstance(max_capture, bool)
                or max_capture <= 0
                or max_capture > 1048576
            ):
                failures.append(
                    "runtime_safety.child_diagnostics.max_capture_bytes must be in 1..1048576"
                )
            probe = diagnostics.get("probe")
            failures.extend(_validate_probe_shape("runtime_safety.child_diagnostics.probe", probe, source))
            receipt_path = diagnostics.get("receipt_path")
            if not isinstance(receipt_path, str) or not receipt_path:
                failures.append("runtime_safety.child_diagnostics.receipt_path is required")
            elif isinstance(probe, dict) and isinstance(max_capture, int):
                probes.append(
                    _normalise_safety_probe(
                        "durable_bounded_child_diagnostics",
                        probe,
                        {
                            "kind": "child_diagnostics",
                            "receipt_path": receipt_path,
                            "max_capture_bytes": max_capture,
                        },
                    )
                )
        elif mode != "not_applicable":
            failures.append(
                "runtime_safety.child_diagnostics.mode must be not_applicable when no subprocess is detected"
            )

    media = runtime_safety.get("media")
    if not isinstance(media, dict):
        failures.append("runtime_safety.media must be an object")
    else:
        promised = media.get("promised_mp4_outputs")
        if has_media:
            if not isinstance(promised, list) or not promised or any(
                not isinstance(path, str) or not path.lower().endswith(".mp4") for path in promised
            ):
                failures.append(
                    "MP4 release code requires a nonempty promised_mp4_outputs list"
                )
                promised = []
            elif len(promised) != len(set(promised)):
                failures.append("runtime_safety.media.promised_mp4_outputs must be unique")
            probe = media.get("probe")
            failures.extend(_validate_probe_shape("runtime_safety.media.probe", probe, source))
            if isinstance(probe, dict):
                declared_mp4s = {
                    output.get("path")
                    for output in probe.get("required_outputs", [])
                    if isinstance(output, dict) and output.get("kind") == "mp4"
                }
                if set(promised) != declared_mp4s:
                    failures.append(
                        "media probe kind=mp4 outputs must exactly equal promised_mp4_outputs"
                    )
                probes.append(
                    _normalise_safety_probe(
                        "media_full_decode",
                        probe,
                        {"kind": "media", "promised_mp4_outputs": list(promised)},
                    )
                )
        elif promised not in (None, []):
            failures.append(
                "runtime_safety.media.promised_mp4_outputs must be empty when no MP4 release path is detected"
            )

    return failures, probes, detected


def validate_profile(
    profile_path: Path,
    profile: dict[str, Any],
    lmt_path: Path,
    lmt_policy: dict[str, Any],
) -> dict[str, Any]:
    base = profile_path.parent.resolve()
    failures: list[str] = []
    warnings: list[str] = []
    context: dict[str, Any] = {
        "lmt_path": lmt_path,
        "lmt_policy": lmt_policy,
    }
    if profile.get("schema") != SCHEMA:
        failures.append(f"schema must equal {SCHEMA}")

    kernel = profile.get("kernel")
    if not isinstance(kernel, dict):
        return {"failures": ["kernel must be an object"], "warnings": warnings, "context": context}
    try:
        kernel_dir = resolve(base, str(kernel["directory"]))
        metadata_path = kernel_dir / str(kernel.get("metadata_file", "kernel-metadata.json"))
        entrypoint = kernel_dir / str(kernel["entrypoint"])
    except KeyError as exc:
        return {"failures": [f"kernel missing required key: {exc}"], "warnings": warnings, "context": context}
    context.update(kernel_dir=kernel_dir, metadata_path=metadata_path, entrypoint=entrypoint)
    if not kernel_dir.is_dir():
        failures.append(f"kernel directory missing: {kernel_dir}")
        return {"failures": failures, "warnings": warnings, "context": context}
    if not metadata_path.is_file():
        failures.append(f"metadata file missing: {metadata_path}")
    if not entrypoint.is_file():
        failures.append(f"entrypoint missing: {entrypoint}")
    if failures:
        return {"failures": failures, "warnings": warnings, "context": context}

    metadata = load_json(metadata_path)
    source = source_text(entrypoint)
    context.update(metadata=metadata, source=source)
    provider_source_failures, provider_sources = derive_provider_sources(metadata)
    failures.extend(provider_source_failures)
    provider_sources_by_key = {
        (item["source_type"], item["source_id"]): item for item in provider_sources
    }
    context["provider_sources"] = provider_sources
    host_path_failures, host_path_evidence = validate_profile_host_path_provenance(
        profile,
        [item["canonical_root"] for item in provider_sources],
    )
    failures.extend(host_path_failures)
    context["host_path_provenance"] = host_path_evidence
    if sha256_file(entrypoint) != kernel.get("artifact_sha256"):
        failures.append("entrypoint SHA-256 drift")
    if sha256_file(metadata_path) != kernel.get("metadata_sha256"):
        failures.append("metadata SHA-256 drift")
    if inventory_sha256(kernel_dir) != kernel.get("package_inventory_sha256"):
        failures.append("package inventory SHA-256 drift")
    failures.extend(exact_subset(metadata, kernel.get("expected_metadata", {})))
    code_file = metadata.get("code_file")
    if isinstance(code_file, str) and Path(code_file).name != entrypoint.name:
        failures.append("metadata code_file does not name the certified entrypoint")
    kernel_id = metadata.get("id")
    title = metadata.get("title")
    if (
        isinstance(kernel_id, str)
        and "/" in kernel_id
        and isinstance(title, str)
        and title_slug(title) != kernel_id.split("/", 1)[1]
    ):
        failures.append("normalized kernel title does not equal declared ID slug")
    if kernel.get("expected_metadata", {}).get("enable_internet") is not False:
        failures.append("expected_metadata must pin enable_internet to false")
    transport = kernel.get("upload_transport")
    if transport != KAGGLE_CLI_SAVE_KERNEL_TRANSPORT:
        failures.append(
            "kernel.upload_transport must equal "
            f"{KAGGLE_CLI_SAVE_KERNEL_TRANSPORT}"
        )
    kernel_type = metadata.get("kernel_type")
    if kernel_type not in {"script", "notebook"}:
        failures.append("metadata kernel_type must be script or notebook")
    context["upload_transport"] = transport
    context["remote_transmitted_files"] = [entrypoint.name]
    command = kernel.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(v, str) and v for v in command):
        failures.append("kernel.command must be a nonempty argv string list")

    try:
        tree = ast.parse(source, filename=str(entrypoint))
    except SyntaxError as exc:
        failures.append(f"entrypoint syntax error: {exc}")
        tree = ast.Module(body=[], type_ignores=[])
    literal_strings: dict[str, str] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            if isinstance(value, str):
                literal_strings[node.targets[0].id] = value
    for name, value in sorted(literal_strings.items()):
        if not name.endswith("_SOURCE"):
            continue
        digest_name = f"{name}_SHA256"
        declared = literal_strings.get(digest_name)
        if declared is None:
            continue
        observed = sha256_bytes(value.encode("utf-8"))
        if declared != observed:
            failures.append(
                f"embedded source literal/hash drift: {name} != {digest_name}"
            )
    forbidden = list(DEFAULT_FORBIDDEN) + list(kernel.get("forbidden_source_fragments", []))
    for fragment in dict.fromkeys(forbidden):
        if fragment and fragment in source:
            failures.append(f"forbidden broad or project-declared source fragment: {fragment}")
    for fragment in NETWORK_FRAGMENTS:
        if fragment in source:
            failures.append(f"network-capable release-path source fragment: {fragment}")
    sibling_modules = {p.stem for p in kernel_dir.glob("*.py") if p.resolve() != entrypoint.resolve()}
    overlap = sorted(imported_roots(tree) & sibling_modules)
    if kernel.get("self_contained") is not True:
        failures.append("kernel.self_contained must be true")
    if overlap:
        failures.append(f"entrypoint imports sibling Python modules: {overlap}")

    step0 = kernel.get("step0", {})
    marker = step0.get("assignment_marker") if isinstance(step0, dict) else None
    if not isinstance(marker, str) or not marker or marker not in source:
        failures.append("declared Step 0 assignment marker is absent")
        marker_line = -1
    else:
        marker_line = source[: source.index(marker)].count("\n") + 1
    heavy_imports = set(step0.get("heavy_imports", [])) if isinstance(step0, dict) else set()
    if marker_line > 0:
        for node in getattr(tree, "body", []):
            if getattr(node, "lineno", 10**9) >= marker_line:
                break
            roots: set[str] = set()
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".", 1)[0])
            early = sorted(roots & heavy_imports)
            if early:
                failures.append(f"heavy import before Step 0: {early}")
    heavy_marker = step0.get("heavy_work_marker") if isinstance(step0, dict) else None
    if not isinstance(heavy_marker, str) or not heavy_marker or heavy_marker not in source:
        failures.append("declared heavy-work marker is absent from source")
    step0_completion_marker = (
        step0.get("completion_marker") if isinstance(step0, dict) else None
    )
    if (
        not isinstance(step0_completion_marker, str)
        or not step0_completion_marker
        or step0_completion_marker not in source
    ):
        failures.append("declared Step0 completion marker is absent from source")
    step0_receipt_path = step0.get("receipt_path") if isinstance(step0, dict) else None
    if not isinstance(step0_receipt_path, str) or not step0_receipt_path:
        failures.append("kernel.step0.receipt_path must be nonempty")
    else:
        try:
            safe_output_path(Path("/step0"), step0_receipt_path)
        except CertifierError as exc:
            failures.append(f"kernel.step0.receipt_path: {exc}")
        if step0_receipt_path not in source:
            failures.append("declared Step0 receipt path is absent from source")
    step0_invariants = (
        step0.get("deterministic_invariants") if isinstance(step0, dict) else None
    )
    if (
        not isinstance(step0_invariants, list)
        or not step0_invariants
        or any(not isinstance(value, str) or not value for value in step0_invariants)
    ):
        failures.append(
            "kernel.step0.deterministic_invariants must be a nonempty string list"
        )
        step0_invariants = []
    elif len(step0_invariants) != len(set(step0_invariants)):
        failures.append("kernel.step0.deterministic_invariants must be unique")
    missing_step0_invariants = sorted(
        REQUIRED_STEP0_INVARIANTS - set(step0_invariants)
    )
    if missing_step0_invariants:
        failures.append(
            "kernel.step0.deterministic_invariants omits required gates: "
            f"{missing_step0_invariants}"
        )
    for invariant in step0_invariants:
        if invariant not in source:
            failures.append(
                f"Step0 deterministic invariant identifier is absent from source: {invariant}"
            )
    step0_probe = step0.get("probe") if isinstance(step0, dict) else None
    failures.extend(_validate_probe_shape("kernel.step0.probe", step0_probe, source))
    if isinstance(step0_probe, dict):
        probe_output_paths = {
            output.get("path")
            for output in step0_probe.get("required_outputs", [])
            if isinstance(output, dict)
        }
        if step0_receipt_path not in probe_output_paths:
            failures.append("kernel.step0.probe must require the Step0 receipt")
        normalised_step0_probe = copy.deepcopy(step0_probe)
        normalised_step0_probe.update(
            {
                "name": "step0_preheavy",
                "role": "step0",
                "workload_units": 1,
                "repeats": 1,
            }
        )
        context["step0_probe"] = normalised_step0_probe

    controls = kernel.get("execution_control_env")
    if not isinstance(controls, list) or not controls or not all(isinstance(k, str) and k for k in controls):
        failures.append("kernel.execution_control_env must be a nonempty string list")
        controls = []
    for key in controls:
        if key not in source:
            failures.append(f"execution-control environment key absent from source: {key}")

    mounts = profile.get("mounts")
    if not isinstance(mounts, list) or not mounts:
        failures.append("mounts must be a nonempty list")
        mounts = []
    names: set[str] = set()
    mounted_provider_keys: set[tuple[str, str]] = set()
    derived_mount_roots: dict[str, str] = {}
    provider_layouts: dict[str, Any] = {}
    numeric_namespace_ids: set[str] = set()
    numeric_namespace_roots: set[tuple[str, str]] = set()
    for index, mount in enumerate(mounts):
        label = f"mounts[{index}]"
        if not isinstance(mount, dict):
            failures.append(f"{label} must be an object")
            continue
        name = mount.get("name")
        remote = mount.get("remote_root")
        if not isinstance(name, str) or not name or name in names:
            failures.append(f"{label}.name must be unique and nonempty")
        else:
            names.add(name)
        if not isinstance(remote, str) or not remote.startswith("/kaggle/input/") or ".." in Path(remote).parts:
            failures.append(f"{label}.remote_root must be an absolute /kaggle/input path")
        elif remote not in source and f"{{mount:{name}}}" not in " ".join(command or []):
            failures.append(f"{label}.remote_root is not bound in source or command")
        layout = mount.get("provider_layout")
        if isinstance(layout, dict):
            provider_key = (layout.get("source_type"), layout.get("source_id"))
        else:
            provider_key = (None, None)
        provider_source = provider_sources_by_key.get(provider_key)
        if provider_source is not None:
            typed_provider_key = (provider_source["source_type"], provider_source["source_id"])
            if typed_provider_key in mounted_provider_keys:
                failures.append(f"{label} duplicates metadata provider source: {provider_source['source_id']}")
            else:
                mounted_provider_keys.add(typed_provider_key)
            if isinstance(name, str) and name:
                derived_mount_roots[name] = provider_source["canonical_root"]
        try:
            local = resolve(base, str(mount["local_root"]))
        except KeyError:
            failures.append(f"{label}.local_root missing")
            continue
        if not local.is_dir():
            failures.append(f"{label}.local_root missing: {local}")
            continue
        observed_inventory = inventory_sha256(local)
        if mount.get("inventory_sha256") != observed_inventory:
            failures.append(f"{label} inventory SHA-256 drift")
        layout_failures, layout_summary = validate_provider_layout(
            label=label,
            mount=mount,
            local_root=local,
            remote_root=str(remote),
            project_root=lmt_path.parent.resolve(),
            provider_source=provider_source,
        )
        failures.extend(layout_failures)
        if isinstance(name, str) and layout_summary is not None:
            provider_layouts[name] = layout_summary
        required = mount.get("required_files", [])
        if not isinstance(required, list) or not required:
            failures.append(f"{label}.required_files must be nonempty")
            continue
        for record in required:
            if not isinstance(record, dict) or not isinstance(record.get("path"), str):
                failures.append(f"{label} has malformed required file record")
                continue
            rel = Path(record["path"])
            if rel.is_absolute() or ".." in rel.parts:
                failures.append(f"{label} required file path escapes mount")
                continue
            target = local / rel
            if not target.is_file():
                failures.append(f"{label} required file missing: {rel.as_posix()}")
                continue
            if "bytes" in record and target.stat().st_size != record["bytes"]:
                failures.append(f"{label} required file byte drift: {rel.as_posix()}")
            if "sha256" in record and sha256_file(target) != record["sha256"]:
                failures.append(f"{label} required file SHA drift: {rel.as_posix()}")
        numeric_namespaces = mount.get("numeric_indexed_namespaces", [])
        if not isinstance(numeric_namespaces, list):
            failures.append(f"{label}.numeric_indexed_namespaces must be a list")
            numeric_namespaces = []
        for namespace_index, contract in enumerate(numeric_namespaces):
            namespace_label = f"{label}.numeric_indexed_namespaces[{namespace_index}]"
            if not isinstance(contract, dict):
                failures.append(f"{namespace_label} must be an object")
                continue
            namespace_id = contract.get("id")
            if (
                not isinstance(namespace_id, str)
                or not namespace_id
                or namespace_id in numeric_namespace_ids
            ):
                failures.append(f"{namespace_label}.id must be globally unique and nonempty")
            else:
                numeric_namespace_ids.add(namespace_id)
            try:
                expected_names = numeric_namespace_expected_names(contract)
                instances = numeric_namespace_instances(contract)
            except CertifierError as exc:
                failures.append(f"{namespace_label}: {exc}")
                continue
            for instance_index, instance in enumerate(instances):
                instance_label = f"{namespace_label}.instances[{instance_index}]"
                relative_root = instance["relative_root"]
                root_key = (str(name), relative_root)
                if root_key in numeric_namespace_roots:
                    failures.append(
                        f"{instance_label} expanded root is not exclusive within its mount"
                    )
                    continue
                numeric_namespace_roots.add(root_key)
                namespace_root = local / relative_root
                if not namespace_root.is_dir() or namespace_root.is_symlink():
                    failures.append(f"{instance_label} local namespace root is missing or unsafe")
                    continue
                entries = sorted(namespace_root.iterdir(), key=lambda path: path.name)
                if contract.get("entry_kind") == "file":
                    wrong_kind = any(
                        not path.is_file() or path.is_symlink() for path in entries
                    )
                else:
                    wrong_kind = any(
                        not path.is_dir() or path.is_symlink() for path in entries
                    )
                if wrong_kind:
                    failures.append(
                        f"{instance_label} must contain only direct real "
                        f"{contract.get('entry_kind')} entries"
                    )
                observed_names = [path.name for path in entries]
                if set(observed_names) != set(expected_names):
                    failures.append(
                        f"{instance_label} local mirror is not the exact declared full cardinality"
                    )
    missing_provider_keys = sorted(set(provider_sources_by_key) - mounted_provider_keys)
    if missing_provider_keys:
        failures.append(f"kernel metadata provider sources lack exactly one mount: {missing_provider_keys}")
    if len(mounts) != len(provider_sources):
        failures.append("mounts must map 1:1 onto metadata dataset_sources and competition_sources")
    context["provider_layouts"] = provider_layouts
    context["derived_mount_roots"] = derived_mount_roots

    scenarios = profile.get("scenarios")
    if not isinstance(scenarios, list):
        failures.append("scenarios must be a list")
        scenarios = []
    scenario_names: set[str] = set()
    roles: set[str] = set()
    for index, scenario in enumerate(scenarios):
        label = f"scenarios[{index}]"
        if not isinstance(scenario, dict):
            failures.append(f"{label} must be an object")
            continue
        name = scenario.get("name")
        role = scenario.get("role")
        if not isinstance(name, str) or not name or name in scenario_names:
            failures.append(f"{label}.name must be unique and nonempty")
        else:
            scenario_names.add(name)
        if role not in REQUIRED_ROLES:
            failures.append(f"{label}.role must be one of {sorted(REQUIRED_ROLES)}")
        else:
            roles.add(role)
        for key in ("workload_units", "timeout_seconds", "repeats"):
            value = scenario.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                failures.append(f"{label}.{key} must be a positive integer")
        if isinstance(scenario.get("repeats"), int) and scenario["repeats"] < 2:
            failures.append(f"{label}.repeats must be at least 2")
        env = scenario.get("env")
        if not isinstance(env, dict) or not any(key in env for key in controls):
            failures.append(f"{label}.env must set at least one declared execution control")
        outputs = scenario.get("required_outputs")
        if not isinstance(outputs, list) or not outputs:
            failures.append(f"{label}.required_outputs must be nonempty")
            outputs = []
        output_paths: set[str] = set()
        byte_repeatable = 0
        for output in outputs:
            if not isinstance(output, dict) or not isinstance(output.get("path"), str):
                failures.append(f"{label} has malformed required output")
                continue
            output_paths.add(output["path"])
            if output.get("kind", "file") not in ALLOWED_KINDS:
                failures.append(f"{label} output has unsupported kind")
            if output["path"].lower().endswith(".mp4") and output.get("kind") != "mp4":
                failures.append(f"{label} MP4 output kind must be 'mp4'")
            repeatability = output.get("repeatability")
            if repeatability not in {"byte", "none"}:
                failures.append(f"{label} output repeatability must be 'byte' or 'none'")
            if repeatability == "byte":
                byte_repeatable += 1
        if outputs and byte_repeatable == 0:
            failures.append(f"{label} must declare at least one byte-repeatable semantic output")
        if (
            isinstance(step0_receipt_path, str)
            and step0_receipt_path not in output_paths
        ):
            failures.append(f"{label} must require the Step0 deterministic-invariant receipt")
        scenario_stdout_markers = scenario.get("stdout_markers", [])
        if (
            isinstance(step0_completion_marker, str)
            and step0_completion_marker not in scenario_stdout_markers
        ):
            failures.append(f"{label} must require the Step0 completion marker")
        completion = scenario.get("completion")
        if not isinstance(completion, dict):
            failures.append(f"{label}.completion must be an object")
        else:
            if completion.get("path") not in output_paths:
                failures.append(f"{label} completion path must be a required output")
            for key in ("status_pointer", "units_pointer"):
                if not isinstance(completion.get(key), str):
                    failures.append(f"{label}.completion.{key} missing")
            if not isinstance(completion.get("success_values"), list) or not completion.get("success_values"):
                failures.append(f"{label}.completion.success_values must be nonempty")
    if roles != REQUIRED_ROLES:
        failures.append(f"scenario roles must cover exactly {sorted(REQUIRED_ROLES)}; observed {sorted(roles)}")

    runtime = profile.get("runtime")
    if not isinstance(runtime, dict):
        failures.append("runtime must be an object")
        runtime = {}
    for retired_key in ("hard_limit_seconds", "max_eligible_fraction", "max_eligible_memory_fraction"):
        if retired_key in runtime:
            failures.append(f"runtime.{retired_key} is retired; autonomous limits come only from LMT.md")
    total_units = _required_number(runtime, "total_workload_units", failures)
    multiplier = _required_number(runtime, "remote_multiplier", failures)
    overhead = _required_number(runtime, "fixed_remote_overhead_seconds", failures, positive=False)
    if overhead < 0:
        failures.append("fixed_remote_overhead_seconds cannot be negative")
    for key in ("min_runs", "min_distinct_workloads"):
        if not isinstance(runtime.get(key), int) or runtime[key] <= 0:
            failures.append(f"runtime.{key} must be a positive integer")
    spread = _required_number(runtime, "max_relative_repeat_spread", failures)
    coverage = _required_number(runtime, "min_largest_sample_fraction", failures)
    memory_limit = _required_number(runtime, "memory_limit_bytes", failures)
    memory_multiplier = _required_number(runtime, "memory_remote_multiplier", failures)
    if spread > 1:
        failures.append("max_relative_repeat_spread cannot exceed 1")
    if coverage > 1:
        failures.append("min_largest_sample_fraction cannot exceed 1")
    if memory_multiplier < 1:
        failures.append("memory_remote_multiplier must be at least 1")
    calibration = runtime.get("calibration", [])
    if not isinstance(calibration, list):
        failures.append("runtime.calibration must be a list")
        calibration = []
    ratios: list[float] = []
    for pair in calibration:
        if not isinstance(pair, dict):
            failures.append("runtime calibration record must be an object")
            continue
        local = pair.get("local_seconds")
        remote = pair.get("remote_seconds")
        if not isinstance(local, (int, float)) or not isinstance(remote, (int, float)) or local <= 0 or remote <= 0:
            failures.append("runtime calibration times must be positive")
        else:
            ratios.append(float(remote) / float(local))
    if not ratios:
        if multiplier < 1.5:
            failures.append("uncalibrated runtime requires remote_multiplier >=1.5")
    elif len(ratios) < 5:
        if multiplier < 1.15 * max(ratios):
            failures.append("1-4 calibration pairs require 1.15x max ratio coverage")
    else:
        if multiplier < 1.10 * percentile(ratios, 0.95):
            failures.append("5+ calibration pairs require 1.10x p95 ratio coverage")
    if scenarios and total_units > 0:
        largest = max(float(s.get("workload_units", 0)) for s in scenarios if isinstance(s, dict))
        if largest > total_units:
            failures.append("scenario workload exceeds total_workload_units")

    adversarial = profile.get("adversarial")
    if not isinstance(adversarial, dict) or adversarial.get("required") is not True:
        failures.append("adversarial.required must be true")
        adversarial = {}
    faults = adversarial.get("faults", [])
    allowed_faults = EXPECTED_FAIL_FAULTS | EXPECTED_PASS_FAULTS
    if not isinstance(faults, list) or not faults:
        failures.append("adversarial.faults must be nonempty")
    elif any(fault not in allowed_faults for fault in faults):
        failures.append(f"adversarial faults must be drawn from {sorted(allowed_faults)}")
    elif numeric_namespace_ids:
        required_numeric_faults = (
            NUMERIC_NAMESPACE_FAIL_FAULTS | NUMERIC_NAMESPACE_PASS_FAULTS
        )
        missing_numeric_faults = sorted(required_numeric_faults - set(faults))
        if missing_numeric_faults:
            failures.append(
                "numeric-indexed namespaces require lexical/missing/extra/alias adversaries: "
                f"{missing_numeric_faults}"
            )
    for key in ("failure_markers", "success_markers", "heavy_work_markers"):
        if not isinstance(adversarial.get(key), list) or not adversarial.get(key):
            failures.append(f"adversarial.{key} must be a nonempty list")

    environment = profile.get("environment", {})
    if not isinstance(environment, dict):
        failures.append("environment must be an object")
        environment = {}
    version_prefix = environment.get("python_version_prefix")
    current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if isinstance(version_prefix, str) and not current_version.startswith(version_prefix):
        failures.append(f"local Python {current_version} does not match required {version_prefix}")
    import_fields: dict[str, set[str]] = {}
    for field in ("required_imports", "carrier_provided_imports", "declared_release_imports"):
        values = environment.get(field, [])
        if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
            failures.append(f"environment.{field} must be a list of nonempty module names")
            values = []
        if len(values) != len(set(values)):
            failures.append(f"environment.{field} must not contain duplicates")
        import_fields[field] = set(values)

    base_imports = import_fields["required_imports"]
    carrier_imports = import_fields["carrier_provided_imports"]
    declared_imports = import_fields["declared_release_imports"]
    if base_imports & carrier_imports:
        failures.append("release imports must have exactly one provider: base runtime or declared carrier")
    provided_imports = base_imports | carrier_imports
    if declared_imports != provided_imports:
        failures.append(
            "environment.declared_release_imports must exactly equal the union of "
            "required_imports and carrier_provided_imports"
        )

    stdlib_imports = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}
    source_release_imports = imported_roots(tree) - stdlib_imports - sibling_modules
    undeclared_source_imports = sorted(source_release_imports - declared_imports)
    if undeclared_source_imports:
        failures.append(
            "entrypoint has undeclared third-party release imports (including function-local imports): "
            f"{undeclared_source_imports}"
        )
    for module in sorted(base_imports):
        if importlib.util.find_spec(module) is None:
            failures.append(f"required local release-path import unavailable: {module!r}")

    dependency_probe = environment.get("release_dependency_probe")
    if declared_imports:
        if not isinstance(dependency_probe, dict):
            failures.append("environment.release_dependency_probe must be an object when release imports are declared")
            dependency_probe = {}
        probe_marker = dependency_probe.get("stdout_marker")
        if not isinstance(probe_marker, str) or not probe_marker or probe_marker not in source:
            failures.append("release dependency probe stdout marker must be nonempty and literal in the entrypoint")
        else:
            for index, scenario in enumerate(scenarios):
                markers = scenario.get("stdout_markers", []) if isinstance(scenario, dict) else []
                if probe_marker not in markers:
                    failures.append(
                        f"scenarios[{index}].stdout_markers must require the release dependency probe marker"
                    )
        carrier_mounts = dependency_probe.get("carrier_mounts", [])
        if not isinstance(carrier_mounts, list) or any(
            not isinstance(name, str) or not name for name in carrier_mounts
        ):
            failures.append("environment.release_dependency_probe.carrier_mounts must be a list of mount names")
            carrier_mounts = []
        invalid_probe_mounts = sorted(set(carrier_mounts) - names)
        if invalid_probe_mounts:
            failures.append(f"release dependency probe references unknown carrier mounts: {invalid_probe_mounts}")
        if carrier_imports and not carrier_mounts:
            failures.append("carrier-provided release imports require at least one declared probe carrier mount")
    elif dependency_probe not in (None, {}):
        failures.append("environment.release_dependency_probe must be absent or empty without release imports")
    safety_failures, safety_probes, safety_detected = validate_runtime_safety_contract(
        profile.get("runtime_safety"),
        source=source,
        tree=tree,
        mount_names=names,
    )
    failures.extend(safety_failures)
    context["runtime_safety_probes"] = safety_probes
    context["runtime_safety_detected"] = safety_detected
    if platform.system() != "Linux":
        warnings.append("local host is not Linux; native-extension ABI and kernel behavior remain unmodeled")
    context["runtime_values"] = {
        "total_units": total_units,
        "multiplier": multiplier,
        "overhead": overhead,
        "memory_limit": memory_limit,
        "memory_multiplier": memory_multiplier,
        "autonomous_projection_cap_hours": float(
            lmt_policy["kaggle"]["autonomous_projection_strictly_below_hours"]
        ),
    }
    return {"failures": failures, "warnings": warnings, "context": context}


def format_token(token: str, values: dict[str, str]) -> str:
    result = token
    for key, value in values.items():
        result = result.replace("{" + key + "}", value)
    unresolved = re.findall(r"\{(?:python|entrypoint|working|sandbox|mount:[^}]+)\}", result)
    if unresolved:
        raise CertifierError(f"unresolved command/environment placeholders: {unresolved}")
    return result


def make_read_only(root: Path) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_file():
            path.chmod(0o444)
        elif path.is_dir():
            path.chmod(0o555)
    root.chmod(0o555)


def write_network_denial(site_dir: Path) -> None:
    site_dir.mkdir(parents=True, exist_ok=True)
    code = """import socket
def _denied(*args, **kwargs):
    raise RuntimeError('SHIP_KAGGLE_KERNELS_NETWORK_DENIED')
socket.create_connection = _denied
socket.getaddrinfo = _denied
_original_socket = socket.socket
class _DeniedSocket(_original_socket):
    def connect(self, *args, **kwargs):
        return _denied(*args, **kwargs)
socket.socket = _DeniedSocket
"""
    (site_dir / "sitecustomize.py").write_text(code, encoding="utf-8")


def safe_output_path(working: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise CertifierError(f"output path escapes working directory: {relative}")
    return working / rel


def json_pointer(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise CertifierError(f"JSON pointer must start with '/': {pointer}")
    current = value
    for raw in pointer[1:].split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(key)]
        elif isinstance(current, dict):
            current = current[key]
        else:
            raise KeyError(key)
    return current


def _mp4_top_level_atoms(path: Path) -> list[str]:
    """Parse bounded top-level ISO-BMFF atom names; decoding proof is receipt-bound below."""

    names: list[str] = []
    size = path.stat().st_size
    offset = 0
    with path.open("rb") as handle:
        while offset + 8 <= size and len(names) < 4096:
            handle.seek(offset)
            header = handle.read(16)
            if len(header) < 8:
                break
            atom_size = int.from_bytes(header[:4], "big")
            atom_name = header[4:8].decode("ascii", errors="replace")
            header_bytes = 8
            if atom_size == 1:
                if len(header) < 16:
                    raise CertifierError("truncated extended MP4 atom")
                atom_size = int.from_bytes(header[8:16], "big")
                header_bytes = 16
            elif atom_size == 0:
                atom_size = size - offset
            if atom_size < header_bytes or offset + atom_size > size:
                raise CertifierError(f"invalid MP4 atom bounds at byte {offset}")
            names.append(atom_name)
            offset += atom_size
    if offset != size:
        raise CertifierError(f"MP4 atom walk ended at {offset} of {size} bytes")
    return names


def _validate_mp4_full_decode_receipt(
    working: Path,
    video_path: Path,
    spec: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    evidence: dict[str, Any] = {}
    receipt_rel = spec.get("full_decode_receipt")
    if not isinstance(receipt_rel, str) or not receipt_rel:
        return [f"MP4 output lacks full_decode_receipt: {spec.get('path')}"], evidence
    try:
        receipt_path = safe_output_path(working, receipt_rel)
    except CertifierError as exc:
        return [str(exc)], evidence
    if not receipt_path.is_file():
        return [f"MP4 full-decode receipt missing: {receipt_rel}"], evidence
    try:
        receipt = load_json(receipt_path)
    except CertifierError as exc:
        return [f"MP4 full-decode receipt malformed: {exc}"], evidence
    expected_video_sha = sha256_file(video_path)
    decoded_frames = receipt.get("decoded_frames")
    expected_frames = receipt.get("expected_frames")
    evidence.update(
        {
            "receipt_path": receipt_rel,
            "receipt_sha256": sha256_file(receipt_path),
            "decoder": receipt.get("decoder"),
            "decoded_frames": decoded_frames,
            "expected_frames": expected_frames,
            "eof_reached": receipt.get("eof_reached"),
        }
    )
    if receipt.get("status") != "PASS":
        failures.append(f"MP4 full-decode receipt is not PASS: {receipt_rel}")
    if receipt.get("video_sha256") != expected_video_sha:
        failures.append(f"MP4 full-decode receipt video SHA mismatch: {receipt_rel}")
    if (
        not isinstance(decoded_frames, int)
        or isinstance(decoded_frames, bool)
        or decoded_frames <= 0
        or not isinstance(expected_frames, int)
        or isinstance(expected_frames, bool)
        or expected_frames <= 0
        or decoded_frames != expected_frames
    ):
        failures.append(f"MP4 full-decode frame count invalid: {receipt_rel}")
    if receipt.get("eof_reached") is not True:
        failures.append(f"MP4 full-decode receipt does not prove EOF: {receipt_rel}")
    if not isinstance(receipt.get("decoder"), str) or not receipt["decoder"].strip():
        failures.append(f"MP4 full-decode receipt lacks decoder identity: {receipt_rel}")
    return failures, evidence


def validate_output(working: Path, spec: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    evidence: dict[str, Any] = {"path": spec.get("path"), "kind": spec.get("kind", "file")}
    try:
        path = safe_output_path(working, str(spec["path"]))
    except (KeyError, CertifierError) as exc:
        return [str(exc)], evidence
    if not path.is_file():
        return [f"required output missing: {spec.get('path')}"], evidence
    cursor = path
    output_symlink = False
    while cursor != working:
        if cursor.is_symlink():
            output_symlink = True
            break
        cursor = cursor.parent
    if output_symlink:
        return [f"required output may not be a symlink: {spec.get('path')}"], evidence
    size = path.stat().st_size
    digest = sha256_file(path)
    evidence.update(bytes=size, sha256=digest)
    if size < int(spec.get("min_bytes", 1)):
        failures.append(f"output too small: {spec['path']}")
    if "max_bytes" in spec and size > int(spec["max_bytes"]):
        failures.append(f"output too large: {spec['path']}")
    if "sha256" in spec and digest != spec["sha256"]:
        failures.append(f"output SHA-256 mismatch: {spec['path']}")
    kind = spec.get("kind", "file")
    parsed: Any = None
    try:
        if kind == "json":
            parsed = json.loads(path.read_text(encoding="utf-8"))
        elif kind == "jsonl":
            lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            parsed = [json.loads(line) for line in lines]
            if not parsed:
                failures.append(f"JSONL output is empty: {spec['path']}")
        elif kind == "csv":
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            if not rows:
                failures.append(f"CSV output is empty: {spec['path']}")
            else:
                evidence["header"] = rows[0]
                evidence["data_rows"] = len(rows) - 1
                if "header" in spec and rows[0] != spec["header"]:
                    failures.append(f"CSV header mismatch: {spec['path']}")
                if "min_rows" in spec and len(rows) - 1 < int(spec["min_rows"]):
                    failures.append(f"CSV has too few rows: {spec['path']}")
        elif kind == "zip":
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                if not names:
                    failures.append(f"ZIP output is empty: {spec['path']}")
                for name in names:
                    member = Path(name)
                    if member.is_absolute() or ".." in member.parts:
                        failures.append(f"ZIP contains unsafe path: {name}")
                evidence["members"] = len(names)
        elif kind == "mp4":
            atoms = _mp4_top_level_atoms(path)
            evidence["top_level_atoms"] = atoms
            if "ftyp" not in atoms or "mdat" not in atoms or "moov" not in atoms:
                failures.append(f"MP4 lacks required ftyp/mdat/moov atoms: {spec['path']}")
            decode_failures, decode_evidence = _validate_mp4_full_decode_receipt(
                working, path, spec
            )
            failures.extend(decode_failures)
            evidence["full_decode"] = decode_evidence
        elif kind != "file":
            failures.append(f"unsupported output kind: {kind}")
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        csv.Error,
        zipfile.BadZipFile,
        CertifierError,
    ) as exc:
        failures.append(f"malformed {kind} output {spec['path']}: {exc}")
    if parsed is not None:
        for pointer, expected in spec.get("json_assertions", {}).items():
            try:
                observed = json_pointer(parsed, pointer)
            except (KeyError, IndexError, ValueError, CertifierError) as exc:
                failures.append(f"JSON assertion missing {pointer} in {spec['path']}: {exc}")
            else:
                if observed != expected:
                    failures.append(f"JSON assertion {pointer} expected {expected!r}, observed {observed!r}")
    return failures, evidence


def validate_runtime_safety_probe_output(
    working: Path,
    contract: Any,
) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    evidence: dict[str, Any] = {}
    if not isinstance(contract, dict):
        return failures, evidence
    kind = contract.get("kind")
    evidence["kind"] = kind
    if kind == "media":
        promised = contract.get("promised_mp4_outputs", [])
        observed = sorted(
            path.relative_to(working).as_posix()
            for path in working.rglob("*.mp4")
            if path.is_file()
        )
        evidence.update(promised_mp4_outputs=promised, observed_mp4_outputs=observed)
        if observed != sorted(promised):
            failures.append(
                "media probe MP4 inventory does not exactly equal promised_mp4_outputs"
            )
        return failures, evidence

    receipt_rel = contract.get("receipt_path")
    if not isinstance(receipt_rel, str) or not receipt_rel:
        return ["runtime-safety probe receipt path is absent"], evidence
    try:
        receipt_path = safe_output_path(working, receipt_rel)
    except CertifierError as exc:
        return [str(exc)], evidence
    if not receipt_path.is_file():
        return [f"runtime-safety probe receipt missing: {receipt_rel}"], evidence
    try:
        receipt = load_json(receipt_path)
    except CertifierError as exc:
        return [f"runtime-safety probe receipt malformed: {exc}"], evidence
    evidence.update(receipt_path=receipt_rel, receipt_sha256=sha256_file(receipt_path))
    if receipt.get("status") != "PASS" or receipt.get("completed_units") != 1:
        failures.append("runtime-safety probe receipt status/completed_units mismatch")

    if kind == "post_heavy_tail":
        required = {
            "exact_outer_entrypoint": True,
            "heavy_handoff_reached": True,
            "post_heavy_tail_executed": True,
            "completion_path_reachable": True,
            "completion_receipt_written": True,
        }
        for key, expected in required.items():
            if receipt.get(key) != expected:
                failures.append(
                    f"post-heavy-tail receipt {key} expected {expected!r}, "
                    f"observed {receipt.get(key)!r}"
                )
        observed_version = receipt.get("python_version")
        version_prefix = contract.get("python_version_prefix")
        if (
            not isinstance(observed_version, str)
            or not isinstance(version_prefix, str)
            or not observed_version.startswith(version_prefix + ".")
        ):
            failures.append("post-heavy-tail receipt target Python version mismatch")
        if receipt.get("entrypoint_marker") != contract.get("entrypoint_marker"):
            failures.append("post-heavy-tail receipt entrypoint marker drift")
        if receipt.get("completion_marker") != contract.get("completion_marker"):
            failures.append("post-heavy-tail receipt completion marker drift")
        if receipt.get("resolved_symbols") != contract.get("required_symbols"):
            failures.append("post-heavy-tail receipt resolved symbol set drift")
        evidence["post_heavy_tail"] = {
            **{key: receipt.get(key) for key in required},
            "python_version": observed_version,
            "entrypoint_marker": receipt.get("entrypoint_marker"),
            "completion_marker": receipt.get("completion_marker"),
            "resolved_symbols": receipt.get("resolved_symbols"),
        }
    elif kind == "subprocess_monitor":
        required = {
            "child_returncode": 0,
            "child_reaped": True,
            "exit_observed_before_rss_error": True,
            "rss_unavailable_after_reap": True,
            "monitor_classification": "CHILD_EXITED_SUCCESS",
        }
        for key, expected in required.items():
            if receipt.get(key) != expected:
                failures.append(
                    f"exit/reap-aware monitor receipt {key} expected {expected!r}, observed {receipt.get(key)!r}"
                )
        evidence["monitor"] = {key: receipt.get(key) for key in required}
    elif kind == "dynamic_module_execution":
        expected_names = contract.get("registered_module_names", [])
        required = {
            "modules_registered_before_exec": True,
            "module_identity_preserved": True,
            "dataclass_definition_loaded": True,
        }
        for key, expected in required.items():
            if receipt.get(key) != expected:
                failures.append(
                    f"dynamic module receipt {key} expected {expected!r}, "
                    f"observed {receipt.get(key)!r}"
                )
        observed_version = receipt.get("python_version")
        version_prefix = contract.get("python_version_prefix")
        if (
            not isinstance(observed_version, str)
            or not isinstance(version_prefix, str)
            or not observed_version.startswith(version_prefix + ".")
        ):
            failures.append("dynamic module receipt target Python version mismatch")
        if receipt.get("registered_module_names") != expected_names:
            failures.append("dynamic module receipt registered module identity drift")
        evidence["dynamic_module_execution"] = {
            **{key: receipt.get(key) for key in required},
            "python_version": observed_version,
            "registered_module_names": receipt.get("registered_module_names"),
        }
    elif kind == "dependency_reexec_lifecycle":
        required = {
            "initial_file_is_regular": True,
            "initial_file_is_symlink": False,
            "dynamic_module_file_is_outer_entrypoint": True,
            "dynamic_module_file_is_regular": True,
            "reexec_target_is_outer_entrypoint": True,
            "wrapper_reentered": True,
            "marker_authenticated": True,
            "completion_path_reachable": True,
            "second_restart_refused": True,
        }
        for key, expected in required.items():
            if receipt.get(key) != expected:
                failures.append(
                    f"dependency re-exec receipt {key} expected {expected!r}, "
                    f"observed {receipt.get(key)!r}"
                )
        observed_version = receipt.get("python_version")
        version_prefix = contract.get("python_version_prefix")
        if (
            not isinstance(observed_version, str)
            or not isinstance(version_prefix, str)
            or not observed_version.startswith(version_prefix + ".")
        ):
            failures.append("dependency re-exec receipt target Python version mismatch")
        if receipt.get("entrypoint_marker") != contract.get("entrypoint_marker"):
            failures.append("dependency re-exec receipt entrypoint marker drift")
        if receipt.get("reexec_module_name") != contract.get("reexec_module_name"):
            failures.append("dependency re-exec receipt module name drift")
        evidence["dependency_reexec_lifecycle"] = {
            **{key: receipt.get(key) for key in required},
            "python_version": observed_version,
            "entrypoint_marker": receipt.get("entrypoint_marker"),
            "reexec_module_name": receipt.get("reexec_module_name"),
            "initial_file_sha256": receipt.get("initial_file_sha256"),
            "reentered_file_sha256": receipt.get("reentered_file_sha256"),
        }
    elif kind == "release_linker_environment":
        raw = contract.get("raw_value", "")
        components = receipt.get("final_components")
        component_sources = receipt.get("component_sources")
        component_exists = receipt.get("component_exists")
        if receipt.get("strategy") != contract.get("mode"):
            failures.append("linker receipt strategy does not match the certified mode")
        if receipt.get("raw_inherited_sha256") != sha256_bytes(str(raw).encode()):
            failures.append("linker receipt does not bind the exact inherited value")
        if receipt.get("unsafe_components_used") is not False:
            failures.append("linker receipt admits unsafe inherited components")
        if not isinstance(components, list) or not components:
            failures.append("linker receipt final_components must be nonempty")
            components = []
        if len(components) != len(set(components)):
            failures.append("linker receipt final_components contains duplicates")
        for component in components:
            if (
                not isinstance(component, str)
                or not component
                or not os.path.isabs(component)
                or os.path.normpath(component) != component
                or "\n" in component
                or "\r" in component
            ):
                failures.append(f"unsafe final linker component: {component!r}")
        trusted_sources = {"authenticated_carrier", "allowlisted_host"}
        if (
            not isinstance(component_sources, list)
            or len(component_sources) != len(components)
            or any(source not in trusted_sources for source in component_sources)
        ):
            failures.append(
                "linker receipt component_sources must bind every final component to authenticated_carrier or allowlisted_host"
            )
            component_sources = []
        if (
            not isinstance(component_exists, list)
            or len(component_exists) != len(components)
            or any(value is not True for value in component_exists)
        ):
            failures.append("linker receipt must prove every final component existed in the target-like probe")
        trusted_roots = contract.get("trusted_roots", [])
        for index, component in enumerate(components):
            if index >= len(component_sources) or not isinstance(component, str):
                continue
            source_kind = component_sources[index]
            roots = [
                root.get("path")
                for root in trusted_roots
                if isinstance(root, dict) and root.get("source") == source_kind
            ]
            confined = False
            for root in roots:
                if not isinstance(root, str) or not os.path.isabs(root):
                    continue
                try:
                    confined = os.path.commonpath([component, root]) == root
                except ValueError:
                    confined = False
                if confined:
                    break
            if not confined:
                failures.append(
                    f"final linker component is outside its authenticated/allowlisted roots: {component!r}"
                )
        evidence["linker"] = {
            "strategy": receipt.get("strategy"),
            "raw_inherited_sha256": receipt.get("raw_inherited_sha256"),
            "final_components": components,
            "component_sources": component_sources,
            "component_exists": component_exists,
            "trusted_roots": trusted_roots,
        }
    elif kind == "child_diagnostics":
        max_capture = int(contract.get("max_capture_bytes", 0))
        child_returncode = receipt.get("child_returncode")
        if not isinstance(child_returncode, int) or isinstance(child_returncode, bool) or child_returncode == 0:
            failures.append("child diagnostic probe must preserve a nonzero child return code")
        if receipt.get("persisted_before_cleanup") is not True:
            failures.append("child diagnostics were not atomically persisted before cleanup")
        stream_evidence: dict[str, Any] = {}
        for stream in ("stdout", "stderr"):
            record = receipt.get(stream)
            if not isinstance(record, dict):
                failures.append(f"child diagnostic receipt lacks {stream} record")
                continue
            path_raw = record.get("path")
            try:
                path = safe_output_path(working, str(path_raw))
            except CertifierError as exc:
                failures.append(str(exc))
                continue
            if not path.is_file():
                failures.append(f"bounded child {stream} diagnostic is missing: {path_raw}")
                continue
            captured = path.stat().st_size
            total = record.get("total_bytes")
            if captured > max_capture:
                failures.append(f"bounded child {stream} diagnostic exceeds max_capture_bytes")
            if record.get("captured_bytes") != captured:
                failures.append(f"child {stream} captured byte count mismatch")
            if record.get("captured_sha256") != sha256_file(path):
                failures.append(f"child {stream} captured SHA-256 mismatch")
            if not isinstance(total, int) or isinstance(total, bool) or total < captured:
                failures.append(f"child {stream} total byte count is invalid")
            full_sha = record.get("full_sha256")
            if not isinstance(full_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", full_sha):
                failures.append(f"child {stream} full SHA-256 is malformed")
            if record.get("truncated") is not (isinstance(total, int) and total > captured):
                failures.append(f"child {stream} truncation flag is inconsistent")
            stream_evidence[stream] = {
                "path": path_raw,
                "total_bytes": total,
                "captured_bytes": captured,
                "captured_sha256": record.get("captured_sha256"),
                "full_sha256": full_sha,
                "truncated": record.get("truncated"),
            }
        evidence["diagnostics"] = {
            "child_returncode": child_returncode,
            "persisted_before_cleanup": receipt.get("persisted_before_cleanup"),
            "streams": stream_evidence,
        }
    else:
        failures.append(f"unknown runtime-safety probe kind: {kind!r}")
    return failures, evidence


def classify_run(returncode: int | None, timed_out: bool, output: str) -> str:
    if timed_out:
        return "RUNTIME_TIMEOUT"
    patterns = (
        ("ModuleNotFoundError", "DEPENDENCY_OFFLINE"),
        ("ImportError", "DEPENDENCY_OFFLINE"),
        ("PermissionError", "FILESYSTEM_PERMISSION"),
        ("FileNotFoundError", "MOUNT_IDENTITY"),
        ("No such file", "MOUNT_IDENTITY"),
        ("projection exceeds", "RUNTIME_ENVELOPE"),
        ("out of memory", "RESOURCE_MEMORY"),
    )
    lowered = output.lower()
    for needle, category in patterns:
        if needle.lower() in lowered:
            return category
    return "PASS" if returncode == 0 else "KERNEL_RUNTIME"


def write_rss_wrapper(site_dir: Path) -> Path:
    wrapper = site_dir / "rss_wrapper.py"
    code = """import resource
import subprocess
import sys
completed = subprocess.run(sys.argv[2:])
peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
units = 'bytes' if sys.argv[1] == 'Darwin' else 'kibibytes'
print(f'__SHIP_KAGGLE_PEAK_RSS__={int(peak)}:{units}', file=sys.stderr)
raise SystemExit(completed.returncode)
"""
    wrapper.write_text(code, encoding="utf-8")
    return wrapper


def timed_command(command: list[str], wrapper: Path) -> tuple[list[str], str]:
    return [sys.executable, str(wrapper), platform.system(), *command], "wrapper"


def parse_peak_rss(stderr: str, timer_kind: str | None) -> int | None:
    if timer_kind == "wrapper":
        match = re.search(r"^__SHIP_KAGGLE_PEAK_RSS__=(\d+):(bytes|kibibytes)$", stderr, re.MULTILINE)
        if match:
            value = int(match.group(1))
            return value if match.group(2) == "bytes" else value * 1024
    return None


def simulate_run(
    profile_path: Path,
    profile: dict[str, Any],
    scenario: dict[str, Any],
    *,
    fault: str | None = None,
) -> dict[str, Any]:
    base = profile_path.parent.resolve()
    kernel = profile["kernel"]
    kernel_dir = resolve(base, kernel["directory"])
    metadata = load_json(kernel_dir / str(kernel.get("metadata_file", "kernel-metadata.json")))
    provider_failures, provider_sources = derive_provider_sources(metadata)
    if provider_failures:
        raise CertifierError("cannot derive simulator provider roots: " + "; ".join(provider_failures))
    provider_sources_by_key = {
        (item["source_type"], item["source_id"]): item for item in provider_sources
    }
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="ship-kaggle-") as temp_name:
        sandbox = Path(temp_name)
        src = sandbox / "kaggle" / "src"
        working = sandbox / "kaggle" / "working"
        src.parent.mkdir(parents=True, exist_ok=True)
        working.mkdir(parents=True, exist_ok=True)
        # `kaggle kernels push` sends metadata plus the declared script/notebook
        # body.  It does not transport arbitrary siblings from the local package
        # directory.  Simulating a full copy made PACKAGE_OMISSION bugs look
        # healthy locally (e.g. a script could read PACKAGE_MANIFEST.json beside
        # itself even though that file will not exist remotely).
        #
        # Keep this hard-coded to the Kaggle CLI transport rather than letting a
        # project profile claim extra local files are uploaded.  Runtime assets
        # must come from declared Kaggle sources/mounts or be embedded in the
        # entrypoint itself.
        if kernel.get("upload_transport") != KAGGLE_CLI_SAVE_KERNEL_TRANSPORT:
            raise CertifierError("unsupported or unvalidated Kaggle upload transport")
        src.mkdir(parents=True, exist_ok=True)
        original_entrypoint = kernel_dir / kernel["entrypoint"]
        staged_entrypoint = src / original_entrypoint.name
        shutil.copy2(original_entrypoint, staged_entrypoint)
        withheld_local_files = sorted(
            path.relative_to(kernel_dir).as_posix()
            for path in kernel_dir.rglob("*")
            if path.is_file() and path.resolve() != original_entrypoint.resolve()
        )
        mount_paths: dict[str, Path] = {}
        derived_remote_roots: dict[str, str] = {}
        fault_applied = False
        numeric_fault_target: dict[str, Any] | None = None
        for index, mount in enumerate(profile["mounts"]):
            layout = mount.get("provider_layout")
            if not isinstance(layout, dict):
                raise CertifierError("simulator refuses a mount without provider provenance")
            provider_key = (layout.get("source_type"), layout.get("source_id"))
            provider_source = provider_sources_by_key.get(provider_key)
            if provider_source is None:
                raise CertifierError("simulator refuses a mount absent from kernel metadata sources")
            # Never trust a profile-authored remote_root when creating the
            # simulated Kaggle tree. The provider root is independently
            # derived from the exact kernel metadata bytes.
            remote = provider_source["canonical_root"]
            staged = sandbox / remote.lstrip("/")
            mount_paths[mount["name"]] = staged
            derived_remote_roots[mount["name"]] = remote
            chosen = index == 0
            if fault == "missing_mount" and chosen:
                fault_applied = True
                continue
            staged.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(resolve(base, mount["local_root"]), staged)
            required = mount.get("required_files", [])
            if chosen and fault in {"missing_required_file", "corrupt_required_file", "duplicate_basename"}:
                if not required:
                    raise CertifierError(f"fault {fault} requires at least one required file")
                target = staged / required[0]["path"]
                if fault == "missing_required_file":
                    target.unlink()
                elif fault == "corrupt_required_file":
                    data = target.read_bytes()
                    target.write_bytes((bytes([data[0] ^ 0xFF]) + data[1:]) if data else b"corrupt")
                else:
                    duplicate = staged / "__adversarial_duplicate__" / target.name
                    duplicate.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, duplicate)
                fault_applied = True
            numeric_namespaces = mount.get("numeric_indexed_namespaces", [])
            if (
                fault in (NUMERIC_NAMESPACE_FAIL_FAULTS | NUMERIC_NAMESPACE_PASS_FAULTS)
                and not fault_applied
                and isinstance(numeric_namespaces, list)
                and numeric_namespaces
            ):
                contract = numeric_namespaces[0]
                instance = numeric_namespace_instances(contract)[0]
                namespace_root = staged / instance["relative_root"]
                expected_names = numeric_namespace_expected_names(contract)
                entry_kind = contract["entry_kind"]
                numeric_fault_target = {
                    "namespace_id": contract["id"],
                    "identity": instance["identity"],
                    "relative_root": instance["relative_root"],
                    "entry_kind": entry_kind,
                    "count": len(expected_names),
                }

                def remove_entry(path: Path) -> None:
                    if entry_kind == "file":
                        path.unlink()
                    else:
                        shutil.rmtree(path)

                def copy_entry(source: Path, destination: Path) -> None:
                    if entry_kind == "file":
                        shutil.copy2(source, destination)
                    else:
                        shutil.copytree(source, destination)

                if fault == "numeric_missing_index":
                    remove_entry(namespace_root / expected_names[-1])
                elif fault == "numeric_extra_index":
                    extra_index = contract["first_index"] + contract["count"]
                    extra_name = contract["filename_template"].format(index=extra_index)
                    copy_entry(
                        namespace_root / expected_names[0], namespace_root / extra_name
                    )
                elif fault == "numeric_alias_index":
                    alias_index = contract["first_index"]
                    alias_name = contract["filename_template"].format(
                        index=f"0{alias_index}"
                    )
                    if alias_name in expected_names:
                        raise CertifierError("numeric alias fault did not create a new spelling")
                    copy_entry(
                        namespace_root / expected_names[0], namespace_root / alias_name
                    )
                else:
                    backup = Path(
                        tempfile.mkdtemp(
                            prefix=".numeric-lexical-order-",
                            dir=namespace_root.parent,
                        )
                    )
                    try:
                        for name in expected_names:
                            copy_entry(namespace_root / name, backup / name)
                        for name in expected_names:
                            remove_entry(namespace_root / name)
                        for name in sorted(expected_names):
                            copy_entry(backup / name, namespace_root / name)
                    finally:
                        shutil.rmtree(backup)
                fault_applied = True
            make_read_only(staged)
        if fault and not fault_applied:
            raise CertifierError(f"fault was not applicable: {fault}")

        raw = staged_entrypoint.read_text(encoding="utf-8")
        replacements = {
            derived_remote_roots[m["name"]]: str(mount_paths[m["name"]])
            for m in profile["mounts"]
        }
        # Typed root diagnostics often reconstruct the canonical root from its
        # provider namespace plus source ID. Rewrite those independently
        # derived namespace literals to the same fresh simulator namespace;
        # never derive either destination from profile.remote_root.
        provider_namespaces = {
            item["source_type"] for item in provider_sources
        }
        if "dataset" in provider_namespaces:
            replacements["/kaggle/input/datasets"] = str(
                sandbox / "kaggle" / "input" / "datasets"
            )
        if "competition" in provider_namespaces:
            replacements["/kaggle/input/competitions"] = str(
                sandbox / "kaggle" / "input" / "competitions"
            )
        replacements["/kaggle/working"] = str(working)
        replacement_pattern = re.compile(
            "|".join(re.escape(value) for value in sorted(replacements, key=len, reverse=True))
        )
        raw = replacement_pattern.sub(lambda match: replacements[match.group(0)], raw)
        staged_entrypoint.write_text(raw, encoding="utf-8")

        site_dir = sandbox / "site"
        write_network_denial(site_dir)
        rss_wrapper = write_rss_wrapper(site_dir)
        env = os.environ.copy()
        for secret in set(profile.get("secrets", [])) | {"KAGGLE_USERNAME", "KAGGLE_KEY"}:
            env.pop(secret, None)
        env.update(
            {
                "PYTHONNOUSERSITE": "1",
                "PIP_NO_INDEX": "1",
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "WANDB_MODE": "offline",
                "NO_PROXY": "*",
                "no_proxy": "*",
                "PYTHONPATH": str(site_dir) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""),
            }
        )
        scenario_python = scenario.get("_python_executable", sys.executable)
        if not isinstance(scenario_python, str) or not Path(scenario_python).is_file():
            raise CertifierError("scenario Python executable is absent or unsafe")
        values = {
            "python": scenario_python,
            "entrypoint": str(staged_entrypoint),
            "working": str(working),
            "sandbox": str(sandbox),
        }
        values.update({f"mount:{name}": str(path) for name, path in mount_paths.items()})
        for key, value in scenario.get("env", {}).items():
            env[str(key)] = format_token(str(value), values)
        command = [format_token(token, values) for token in kernel["command"]]
        measured_command, timer_kind = timed_command(command, rss_wrapper)
        timeout = int(scenario["timeout_seconds"])
        timed_out = False
        try:
            completed = subprocess.run(
                measured_command,
                cwd=working,
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            returncode: int | None = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            returncode = None
            stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        elapsed = time.monotonic() - started
        peak_rss_bytes = parse_peak_rss(stderr, timer_kind)
        combined = stdout + "\n" + stderr
        output_failures: list[str] = []
        output_evidence: list[dict[str, Any]] = []
        for output in scenario.get("required_outputs", []):
            found_failures, evidence = validate_output(working, output)
            output_failures.extend(found_failures)
            output_evidence.append(evidence)
        for pattern in scenario.get("forbidden_outputs", []):
            if list(working.glob(pattern)):
                output_failures.append(f"forbidden output exists: {pattern}")
        runtime_safety_contract = copy.deepcopy(scenario.get("_runtime_safety_contract"))
        if isinstance(runtime_safety_contract, dict):
            for root in runtime_safety_contract.get("trusted_roots", []):
                if isinstance(root, dict) and isinstance(root.get("path"), str):
                    root["path"] = str(Path(format_token(root["path"], values)).resolve())
        safety_failures, safety_evidence = validate_runtime_safety_probe_output(
            working, runtime_safety_contract
        )
        output_failures.extend(safety_failures)

        completion_present = False
        completion_valid = False
        completion_evidence: dict[str, Any] = {}
        completion = scenario.get("completion", {})
        if isinstance(completion, dict) and isinstance(completion.get("path"), str):
            completion_path = safe_output_path(working, completion["path"])
            completion_present = completion_path.is_file()
            if completion_present:
                try:
                    value = json.loads(completion_path.read_text(encoding="utf-8"))
                    status = json_pointer(value, completion["status_pointer"])
                    units = json_pointer(value, completion["units_pointer"])
                    completion_evidence = {"status": status, "units": units}
                    completion_valid = status in completion["success_values"] and units == scenario["workload_units"]
                    if not completion_valid:
                        output_failures.append("completion receipt status or workload units mismatch")
                except (OSError, json.JSONDecodeError, KeyError, IndexError, ValueError, CertifierError) as exc:
                    output_failures.append(f"completion receipt malformed: {exc}")
        step0_failures: list[str] = []
        step0_evidence: dict[str, Any] = {}
        step0_receipt_present = False
        if scenario.get("role") in (REQUIRED_ROLES | {"step0"}):
            if fault in EXPECTED_FAIL_FAULTS:
                step0_path = safe_output_path(
                    working, profile["kernel"]["step0"]["receipt_path"]
                )
                step0_receipt_present = step0_path.is_file()
                step0_evidence = {
                    "receipt_path": profile["kernel"]["step0"]["receipt_path"],
                    "receipt_present": step0_receipt_present,
                }
            else:
                (
                    step0_failures,
                    step0_evidence,
                    step0_receipt_present,
                ) = validate_step0_run(
                    working=working,
                    stdout=stdout,
                    profile=profile,
                    expect_heavy=scenario.get("role") != "step0",
                )
                output_failures.extend(step0_failures)
        marker_failures: list[str] = []
        for marker in scenario.get("stdout_markers", []):
            if marker not in stdout:
                marker_failures.append(f"stdout marker absent: {marker}")
        for marker in scenario.get("stderr_forbidden_markers", []):
            if marker in stderr:
                marker_failures.append(f"forbidden stderr marker present: {marker}")

        if fault in EXPECTED_FAIL_FAULTS:
            adversarial = profile["adversarial"]
            failed_process = timed_out or returncode != 0
            has_failure_marker = any(marker in combined for marker in adversarial["failure_markers"])
            no_success = not any(marker in combined for marker in adversarial["success_markers"])
            no_heavy = not any(marker in combined for marker in adversarial["heavy_work_markers"])
            passed = (
                failed_process
                and has_failure_marker
                and no_success
                and no_heavy
                and not completion_present
                and not step0_receipt_present
            )
            failures = [] if passed else [
                "fault did not fail closed inside Step0 with an explicit failure marker, no heavy work, and no Step0/final receipt"
            ]
        else:
            expected_codes = scenario.get("exit_codes", [0])
            passed = (
                not timed_out
                and returncode in expected_codes
                and not output_failures
                and not marker_failures
                and completion_valid
            )
            failures = output_failures + marker_failures
            if timed_out:
                failures.append("scenario timed out")
            elif returncode not in expected_codes:
                failures.append(f"unexpected exit code: {returncode}")
        return {
            "scenario": scenario["name"],
            "role": scenario["role"],
            "fault": fault,
            "status": "PASS" if passed else "FAIL",
            "failure_class": classify_run(returncode, timed_out, combined),
            "failures": failures,
            "elapsed_seconds": elapsed,
            "peak_rss_bytes": peak_rss_bytes,
            "workload_units": scenario["workload_units"],
            "returncode": returncode,
            "timed_out": timed_out,
            "completion": completion_evidence,
            "outputs": output_evidence,
            "step0": step0_evidence,
            "runtime_safety": safety_evidence,
            "numeric_fault_target": numeric_fault_target,
            "stdout_tail": stdout[-12000:],
            "stderr_tail": stderr[-12000:],
            "upload_materialization": {
                "transport": KAGGLE_CLI_SAVE_KERNEL_TRANSPORT,
                "transmitted_runtime_files": [staged_entrypoint.name],
                "withheld_local_package_files": withheld_local_files,
            },
        }


def runtime_projection(
    profile: dict[str, Any],
    runs: list[dict[str, Any]],
    lmt_policy: dict[str, Any],
) -> dict[str, Any]:
    runtime = profile["runtime"]
    failures: list[str] = []
    good = [run for run in runs if run["status"] == "PASS" and run.get("fault") is None]
    if len(good) < int(runtime["min_runs"]):
        failures.append("insufficient successful timing runs")
    units = sorted({int(run["workload_units"]) for run in good})
    if len(units) < int(runtime["min_distinct_workloads"]):
        failures.append("insufficient distinct workload scales")
    total_units = float(runtime["total_workload_units"])
    largest_fraction = (max(units) / total_units) if units and total_units > 0 else 0.0
    if largest_fraction < float(runtime["min_largest_sample_fraction"]):
        failures.append("largest local scenario covers too little of the full workload")

    spreads: dict[str, float] = {}
    for scenario in sorted({run["scenario"] for run in good}):
        elapsed = [float(run["elapsed_seconds"]) for run in good if run["scenario"] == scenario]
        if len(elapsed) >= 2:
            median = statistics.median(elapsed)
            relative = (max(elapsed) - min(elapsed)) / median if median > 0 else math.inf
            spreads[scenario] = relative
            if relative > float(runtime["max_relative_repeat_spread"]):
                failures.append(f"timing spread too high for scenario {scenario}: {relative:.6f}")
    max_spread = max(spreads.values(), default=0.0)

    slopes: list[float] = []
    for left in good:
        for right in good:
            delta_units = float(right["workload_units"]) - float(left["workload_units"])
            if delta_units > 0:
                slopes.append(max(0.0, (float(right["elapsed_seconds"]) - float(left["elapsed_seconds"])) / delta_units))
    if not slopes:
        failures.append("cannot estimate a multi-scale runtime slope")
        slope_upper = math.inf
        startup_upper = math.inf
    else:
        slope_upper = percentile(slopes, 0.95)
        intercepts = [max(0.0, float(run["elapsed_seconds"]) - slope_upper * float(run["workload_units"])) for run in good]
        startup_upper = percentile(intercepts, 0.95)
    local_upper = startup_upper + slope_upper * total_units
    variability_multiplier = 1.0 + max_spread
    remote_upper = (
        float(runtime["fixed_remote_overhead_seconds"])
        + local_upper * float(runtime["remote_multiplier"]) * variability_multiplier
    )
    threshold = 3600.0 * float(
        lmt_policy["kaggle"]["autonomous_projection_strictly_below_hours"]
    )
    approval_required = math.isfinite(remote_upper) and remote_upper >= threshold
    if not math.isfinite(remote_upper):
        failures.append("projected remote upper envelope is not finite")
    memory_points = [
        (float(run["workload_units"]), float(run["peak_rss_bytes"]))
        for run in good
        if isinstance(run.get("peak_rss_bytes"), int) and run["peak_rss_bytes"] > 0
    ]
    if len(memory_points) < int(runtime["min_runs"]):
        failures.append("peak RSS was not measured for every required timing run")
        projected_memory = math.inf
    else:
        memory_slopes: list[float] = []
        for left_units, left_rss in memory_points:
            for right_units, right_rss in memory_points:
                if right_units > left_units:
                    memory_slopes.append(max(0.0, (right_rss - left_rss) / (right_units - left_units)))
        memory_slope = percentile(memory_slopes, 0.95) if memory_slopes else 0.0
        memory_intercepts = [max(0.0, rss - memory_slope * units_value) for units_value, rss in memory_points]
        projected_memory = (
            percentile(memory_intercepts, 0.95) + memory_slope * total_units
        ) * float(runtime["memory_remote_multiplier"])
    memory_threshold = float(runtime["memory_limit_bytes"])
    if not math.isfinite(projected_memory) or projected_memory > memory_threshold:
        failures.append("projected peak RSS exceeds the eligible memory threshold")
    status = "FAIL" if failures else ("APPROVAL_REQUIRED" if approval_required else "PASS")
    return {
        "status": status,
        "failures": failures,
        "successful_runs": len(good),
        "distinct_workloads": units,
        "largest_sample_fraction": largest_fraction,
        "repeat_relative_spread": spreads,
        "slope_upper_seconds_per_unit": slope_upper,
        "startup_upper_seconds": startup_upper,
        "local_upper_seconds": local_upper,
        "remote_multiplier": runtime["remote_multiplier"],
        "variability_multiplier": variability_multiplier,
        "fixed_remote_overhead_seconds": runtime["fixed_remote_overhead_seconds"],
        "projected_remote_upper_seconds": remote_upper,
        "lmt_autonomous_projection_cap_seconds": threshold,
        "strictly_below_cap_required": True,
        "autonomous_headroom_seconds": threshold - remote_upper,
        "runtime_wall_clock_kill_seconds": None,
        "projected_peak_rss_bytes": projected_memory,
        "physical_memory_limit_bytes": memory_threshold,
        "memory_limit_bytes": runtime["memory_limit_bytes"],
        "memory_headroom_bytes": float(runtime["memory_limit_bytes"]) - projected_memory,
    }


def repeatability_report(profile: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    failures: list[str] = []
    evidence: dict[str, Any] = {}
    scenarios = {scenario["name"]: scenario for scenario in profile["scenarios"]}
    for name, scenario in scenarios.items():
        scenario_runs = [run for run in runs if run.get("fault") is None and run["scenario"] == name and run["status"] == "PASS"]
        by_path = {
            item["path"]: item
            for item in scenario["required_outputs"]
            if item.get("repeatability") == "byte"
        }
        evidence[name] = {}
        for path in by_path:
            hashes = [
                output["sha256"]
                for run in scenario_runs
                for output in run["outputs"]
                if output.get("path") == path and isinstance(output.get("sha256"), str)
            ]
            evidence[name][path] = sorted(set(hashes))
            if len(hashes) != int(scenario["repeats"]):
                failures.append(f"repeatable output evidence incomplete: {name}/{path}")
            elif len(set(hashes)) != 1:
                failures.append(f"byte-repeatable output drift: {name}/{path}")
    pass_fault_runs = [
        run
        for run in runs
        if run.get("fault") in EXPECTED_PASS_FAULTS and run["status"] == "PASS"
    ]
    for adversarial_run in pass_fault_runs:
        baseline = next((run for run in runs if run.get("fault") is None and run["scenario"] == adversarial_run["scenario"] and run["status"] == "PASS"), None)
        if baseline is None:
            failures.append("expected-pass adversarial run lacks a passing baseline")
            continue
        repeatable_paths = {item["path"] for item in scenarios[adversarial_run["scenario"]]["required_outputs"] if item.get("repeatability") == "byte"}
        baseline_hashes = {item["path"]: item.get("sha256") for item in baseline["outputs"] if item.get("path") in repeatable_paths}
        adversarial_hashes = {item["path"]: item.get("sha256") for item in adversarial_run["outputs"] if item.get("path") in repeatable_paths}
        if adversarial_hashes != baseline_hashes:
            failures.append(
                f"{adversarial_run['fault']} changed byte-repeatable outputs"
            )
    return {"status": "PASS" if not failures else "FAIL", "failures": failures, "hashes": evidence}


def certify(profile_path: Path, receipt_path: Path) -> dict[str, Any]:
    profile = load_json(profile_path)
    lmt_path, lmt_policy = profile_lmt(profile_path, profile)
    static = validate_profile(profile_path, profile, lmt_path, lmt_policy)
    runs: list[dict[str, Any]] = []
    runtime_safety_runs: list[dict[str, Any]] = []
    adversarial_runs: list[dict[str, Any]] = []
    step0_preheavy_run: dict[str, Any] = {
        "status": "NOT_RUN",
        "failures": ["static validation failed"],
    }
    projection: dict[str, Any] = {"status": "NOT_RUN", "failures": ["static validation failed"]}
    repeatability: dict[str, Any] = {"status": "NOT_RUN", "failures": ["static validation failed"]}
    if not static["failures"]:
        step0_preheavy_run = simulate_run(
            profile_path, profile, static["context"]["step0_probe"]
        )
        if step0_preheavy_run["status"] == "PASS":
            for probe in static["context"].get("runtime_safety_probes", []):
                runtime_safety_runs.append(simulate_run(profile_path, profile, probe))
            for scenario in profile["scenarios"]:
                for _ in range(int(scenario["repeats"])):
                    runs.append(simulate_run(profile_path, profile, scenario))
            projection = runtime_projection(profile, runs, lmt_policy)
            repeatability = repeatability_report(profile, runs)
            if all(run["status"] == "PASS" for run in runs):
                tiny = next(s for s in profile["scenarios"] if s["role"] == "tiny")
                for fault in profile["adversarial"]["faults"]:
                    adversarial_runs.append(simulate_run(profile_path, profile, tiny, fault=fault))
                repeatability = repeatability_report(profile, runs + adversarial_runs)
    non_runtime_pass = (
        not static["failures"]
        and step0_preheavy_run.get("status") == "PASS"
        and all(run["status"] == "PASS" for run in runtime_safety_runs)
        and runs
        and all(run["status"] == "PASS" for run in runs)
        and repeatability.get("status") == "PASS"
        and adversarial_runs
        and all(run["status"] == "PASS" for run in adversarial_runs)
    )
    all_pass = non_runtime_pass and projection.get("status") == "PASS"
    approval_required = non_runtime_pass and projection.get("status") == "APPROVAL_REQUIRED"
    quick_debug = {
        "name": "focused_pre_push_release_debug",
        "auto_triggered": True,
        "transport": KAGGLE_CLI_SAVE_KERNEL_TRANSPORT,
        "purpose": (
            "exercise the exact Step0-only preheavy boundary and Kaggle CLI "
            "script/notebook materialization: only the "
            "declared entrypoint is present beside the fresh mounts, so undeclared "
            "local package siblings and provider mount-depth drift must fail before "
            "a remote version is spent"
        ),
        "status": "PASS"
        if (
            not static["failures"]
            and step0_preheavy_run.get("status") == "PASS"
            and all(run["status"] == "PASS" for run in runtime_safety_runs)
            and runs
            and all(run["status"] == "PASS" for run in runs)
        )
        else "FAIL",
    }
    all_pass = all_pass and quick_debug["status"] == "PASS"
    approval_required = approval_required and quick_debug["status"] == "PASS"
    receipt_status = "ELIGIBLE" if all_pass else ("APPROVAL_REQUIRED" if approval_required else "REJECTED")
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "status": receipt_status,
        "eligible": bool(all_pass),
        "autonomous_launch_eligible": bool(all_pass),
        "created_unix_seconds": time.time(),
        "profile_path": str(profile_path.resolve()),
        "profile_sha256": sha256_file(profile_path),
        "limits_file": str(lmt_path.resolve()),
        "limits_sha256": sha256_file(lmt_path),
        "autonomous_projection_cap_hours": lmt_policy["kaggle"][
            "autonomous_projection_strictly_below_hours"
        ],
        "kernel_id": static.get("context", {}).get("metadata", {}).get("id"),
        "artifact_sha256": profile.get("kernel", {}).get("artifact_sha256"),
        "metadata_sha256": profile.get("kernel", {}).get("metadata_sha256"),
        "package_inventory_sha256": profile.get("kernel", {}).get("package_inventory_sha256"),
        "static": {"status": "PASS" if not static["failures"] else "FAIL", "failures": static["failures"], "warnings": static["warnings"]},
        "step0_preheavy_run": step0_preheavy_run,
        "simulation_runs": runs,
        "host_path_provenance": static.get("context", {}).get(
            "host_path_provenance", {}
        ),
        "runtime_safety_detection": static.get("context", {}).get("runtime_safety_detected", {}),
        "runtime_safety_runs": runtime_safety_runs,
        "runtime_projection": projection,
        "repeatability": repeatability,
        "adversarial_runs": adversarial_runs,
        "quick_debug": quick_debug,
        "claim_scope": "prevents modeled deterministic Kaggle-CLI materialization/package, control-host command/interpreter path leakage, provider-roundtrip mount topology, Step0 input/inventory/path/cardinality ordering, identity-expanded file/directory numeric-namespace lexical/cardinality/alias drift, offline dependency, target-minor dynamic-module identity, exact post-heavy outer-tail closure, exit/reap monitor, linker-environment, durable-child-diagnostic, promised-MP4 full-decode, execution-control, output-contract, and runtime-envelope failures for the exact recorded bytes",
        "unmodeled_risks": [
            "Kaggle service, scheduler, host, or hardware failure",
            "GPU/device memory and accelerator-specific allocation unless the local runner exercises the same accelerator path",
            "native-extension ABI or Linux behavior when local simulation is not run in a matching Linux image",
            "unrepresented input strata or distribution drift outside the declared mirrors",
        ],
        "launch_rule": "Re-hash exact bytes and LMT.md under the project serial lock; consume this receipt once; refuse any drift. APPROVAL_REQUIRED is not autonomous launch authority.",
    }
    receipt["receipt_content_sha256"] = sha256_bytes(canonical_json(receipt))
    write_json(receipt_path, receipt)
    return receipt


def make_profile(kernel_dir: Path, output: Path) -> dict[str, Any]:
    metadata_path = kernel_dir / "kernel-metadata.json"
    metadata = load_json(metadata_path)
    entry_name = metadata.get("code_file")
    if not isinstance(entry_name, str) or not (kernel_dir / entry_name).is_file():
        candidates = sorted(list(kernel_dir.glob("*.py")) + list(kernel_dir.glob("*.ipynb")))
        if len(candidates) != 1:
            raise CertifierError("cannot infer one entrypoint; set metadata code_file or leave exactly one .py/.ipynb")
        entry_name = candidates[0].name
    entrypoint = kernel_dir / entry_name
    expected_keys = ("id", "title", "code_file", "kernel_type", "enable_gpu", "enable_internet", "dataset_sources", "competition_sources", "kernel_sources")
    expected = {key: metadata[key] for key in expected_keys if key in metadata}
    expected["enable_internet"] = False
    relative_kernel = os.path.relpath(kernel_dir.resolve(), output.parent.resolve())
    lmt_path = find_lmt(kernel_dir)
    profile = {
        "schema": SCHEMA,
        "limits_file": os.path.relpath(lmt_path, output.parent.resolve()),
        "kernel": {
            "directory": relative_kernel,
            "metadata_file": "kernel-metadata.json",
            "entrypoint": entry_name,
            "artifact_sha256": sha256_file(entrypoint),
            "metadata_sha256": sha256_file(metadata_path),
            "package_inventory_sha256": inventory_sha256(kernel_dir),
            "upload_transport": KAGGLE_CLI_SAVE_KERNEL_TRANSPORT,
            "command": ["{python}", "{entrypoint}"] if entrypoint.suffix == ".py" else ["REPLACE_WITH_NONINTERACTIVE_NOTEBOOK_RUNNER", "{entrypoint}"],
            "expected_metadata": expected,
            "self_contained": True,
            "step0": {
                "assignment_marker": "STEP0 = run_step0()",
                "heavy_imports": ["numpy", "pandas", "scipy", "torch", "torchvision", "zarr"],
                "heavy_work_marker": "heavy_work_started",
                "completion_marker": "REPLACE_WITH_STEP0_INVARIANTS_PASS_MARKER",
                "receipt_path": "step0-invariants.json",
                "deterministic_invariants": [
                    "input_identity",
                    "inventory",
                    "path_topology",
                    "cardinality",
                ],
                "probe": {},
            },
            "execution_control_env": ["KAGGLE_PREFLIGHT_UNITS"],
            "forbidden_source_fragments": [],
        },
        "mounts": [],
        "scenarios": [],
        "runtime": {
            "total_workload_units": 1,
            "remote_multiplier": 1.5,
            "fixed_remote_overhead_seconds": 120,
            "min_runs": 8,
            "min_distinct_workloads": 4,
            "max_relative_repeat_spread": 0.25,
            "min_largest_sample_fraction": 0.02,
            "memory_limit_bytes": 17179869184,
            "memory_remote_multiplier": 1.25,
            "calibration": [],
        },
        "adversarial": {
            "required": True,
            "faults": ["missing_mount", "missing_required_file", "corrupt_required_file", "duplicate_basename"],
            "failure_markers": ["KernelError", "FAIL_CLOSED", "Traceback"],
            "success_markers": ["stage_end"],
            "heavy_work_markers": ["heavy_work_started"],
        },
        "environment": {
            "python_version_prefix": f"{sys.version_info.major}.{sys.version_info.minor}",
            "required_imports": [],
            "carrier_provided_imports": [],
            "declared_release_imports": [],
            "release_dependency_probe": {},
        },
        "runtime_safety": {
            "post_heavy_tail": {
                "mode": "exact_outer_entrypoint_probe",
                "python_executable": "{python}",
                "python_version_prefix": f"{sys.version_info.major}.{sys.version_info.minor}",
                "entrypoint_marker": "REPLACE_WITH_POST_HEAVY_HANDOFF_MARKER",
                "completion_marker": "REPLACE_WITH_FINAL_COMPLETION_MARKER",
                "required_symbols": ["REPLACE_WITH_OUTER_TAIL_HELPER"],
                "receipt_path": "post-heavy-tail.json",
                "probe": {},
            },
            "dynamic_module_execution": {"mode": "not_applicable"},
            "subprocess_monitor": {"mode": "not_applicable"},
            "release_linker_environment": {"mode": "not_applicable"},
            "child_diagnostics": {"mode": "not_applicable"},
            "media": {"promised_mp4_outputs": []},
        },
        "secrets": ["KAGGLE_USERNAME", "KAGGLE_KEY"],
    }
    write_json(output, profile)
    return profile


def _write_fixture_lmt(root: Path, cap_hours: float = 8.0) -> Path:
    policy = {
        "schema": "cell-tracking.autonomy-limits.v1",
        "effective_date": "self-test",
        "kaggle": {
            "autonomous_projection_strictly_below_hours": cap_hours,
            "weekly_gpu_budget_hours": 30.0,
            "auto_approved_wall_clock_kill_seconds": None,
        },
    }
    path = root / "LMT.md"
    path.write_text(
        "# Self-test LMT\n\n"
        + LMT_POLICY_BEGIN
        + "\n```json\n"
        + json.dumps(policy, indent=2, sort_keys=True)
        + "\n```\n"
        + LMT_POLICY_END
        + "\n",
        encoding="utf-8",
    )
    return path


def _fixture_profile(root: Path) -> tuple[Path, dict[str, Any]]:
    _write_fixture_lmt(root)
    kernel_dir = root / "kernel"
    input_dir = root / "input"
    competition_dir = root / "competition_input"
    kernel_dir.mkdir(parents=True)
    input_dir.mkdir()
    competition_dir.mkdir()
    manifest = input_dir / "manifest.json"
    manifest.write_text('{"fixture":"ok"}\n', encoding="utf-8")
    manifest_sha = sha256_file(manifest)
    competition_sentinel = competition_dir / "sentinel.txt"
    competition_sentinel.write_text("dual-root-ok\n", encoding="utf-8")
    competition_sentinel_sha = sha256_file(competition_sentinel)
    numeric_file_dir = competition_dir / "numeric_files"
    numeric_file_dir.mkdir()
    for index in range(21):
        (numeric_file_dir / f"{index}.json").write_text(
            json.dumps({"index": index}) + "\n", encoding="utf-8"
        )
    raw_identities = tuple(f"44b6_fixture_{index:02d}" for index in range(21))
    raw_expected_names = [str(index) for index in range(100)]
    for identity in raw_identities:
        raw_numeric_root = competition_dir / f"train/{identity}.zarr/0/c"
        raw_numeric_root.mkdir(parents=True)
        for name in sorted(raw_expected_names):
            entry = raw_numeric_root / name
            entry.mkdir()
    raw_numeric_contract = {
        "id": "raw_frames",
        "entry_kind": "directory",
        "root_template": "train/{identity}.zarr/0/c",
        "identities": list(raw_identities),
        "filename_template": "{index}",
        "first_index": 0,
        "count": 100,
    }
    file_numeric_contract = {
        "id": "numbered_files",
        "entry_kind": "file",
        "relative_root": "numeric_files",
        "filename_template": "{index}.json",
        "first_index": 0,
        "count": 21,
    }
    raw_contract_receipt = numeric_namespace_contract_receipt(raw_numeric_contract)
    file_contract_receipt = numeric_namespace_contract_receipt(file_numeric_contract)
    embedded_source = '''from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Payload:
    value: int
'''
    embedded_source_sha = sha256_bytes(embedded_source.encode("utf-8"))
    source = f'''import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types

EMBEDDED_SOURCE = {embedded_source!r}
EMBEDDED_SOURCE_SHA256 = "{embedded_source_sha}"

class KernelError(RuntimeError):
    pass

INPUT = Path("/kaggle/input/datasets/demo/input")
COMPETITION = Path("/kaggle/input/competitions/demo-competition")
COMPETITION_NAMESPACE = Path("/kaggle/input/competitions")
WORKING = Path("/kaggle/working")
EXPECTED = "{manifest_sha}"
COMPETITION_EXPECTED = "{competition_sentinel_sha}"
RAW_IDENTITIES = {raw_identities!r}
RAW_CONTRACT_SHA256 = "{raw_contract_receipt['contract_sha256']}"
FILE_CONTRACT_SHA256 = "{file_contract_receipt['contract_sha256']}"

def run_step0():
    manifest = INPUT / "manifest.json"
    if not manifest.is_file():
        raise KernelError("FAIL_CLOSED missing manifest")
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != EXPECTED:
        raise KernelError("FAIL_CLOSED corrupt manifest")
    competition_sentinel = COMPETITION / "sentinel.txt"
    if not competition_sentinel.is_file():
        raise KernelError("FAIL_CLOSED missing competition sentinel")
    if hashlib.sha256(competition_sentinel.read_bytes()).hexdigest() != COMPETITION_EXPECTED:
        raise KernelError("FAIL_CLOSED corrupt competition sentinel")
    if COMPETITION.parent != COMPETITION_NAMESPACE:
        raise KernelError("FAIL_CLOSED partial competition-root inverse")
    raw_instances = []
    raw_expected_names = [str(index) for index in range(100)]
    for identity in RAW_IDENTITIES:
        relative_root = f"train/{{identity}}.zarr/0/c"
        numeric_root = COMPETITION / relative_root
        entries = list(numeric_root.iterdir())
        actual_names = [path.name for path in entries]
        if (
            any(not path.is_dir() or path.is_symlink() for path in entries)
            or set(actual_names) != set(raw_expected_names)
        ):
            raise KernelError(
                "FAIL_CLOSED raw directory numeric inventory/cardinality/path topology"
            )
        ordered_names = sorted(actual_names, key=int)
        raw_instances.append({{
            "identity": identity,
            "relative_root": relative_root,
            "count": len(ordered_names),
            "ordered_names": ordered_names,
        }})
    file_root = COMPETITION / "numeric_files"
    file_entries = list(file_root.iterdir())
    actual_file_names = [path.name for path in file_entries]
    expected_file_names = [f"{{index}}.json" for index in range(21)]
    if (
        any(not path.is_file() or path.is_symlink() for path in file_entries)
        or set(actual_file_names) != set(expected_file_names)
    ):
        raise KernelError("FAIL_CLOSED file numeric inventory/cardinality/path topology")
    ordered_file_names = sorted(
        actual_file_names, key=lambda name: int(name.removesuffix(".json"))
    )
    step0_receipt = {{
        "status": "PASS",
        "completed_units": 1,
        "invariants": ["input_identity", "inventory", "path_topology", "cardinality"],
        "numeric_namespaces": {{
            "raw_frames": {{
                "contract_sha256": RAW_CONTRACT_SHA256,
                "entry_kind": "directory",
                "count": 100,
                "instances": raw_instances,
            }},
            "numbered_files": {{
                "contract_sha256": FILE_CONTRACT_SHA256,
                "entry_kind": "file",
                "count": len(ordered_file_names),
                "instances": [{{
                    "identity": None,
                    "relative_root": "numeric_files",
                    "count": len(ordered_file_names),
                    "ordered_names": ordered_file_names,
                }}],
            }},
        }},
    }}
    WORKING.mkdir(parents=True, exist_ok=True)
    (WORKING / "step0-invariants.json").write_text(
        json.dumps(step0_receipt, sort_keys=True)
    )
    print("STEP0_INVARIANTS_PASS")
    return {{"ok": True}}

STEP0 = run_step0()

if os.environ.get("SHIP_STEP0_ONLY") == "1":
    raise SystemExit(0)

def run_post_heavy_tail(units, proof=False):
    WORKING.mkdir(parents=True, exist_ok=True)
    if proof:
        import platform
        receipt = {{
            "status": "PASS", "completed_units": 1,
            "python_version": platform.python_version(),
            "entrypoint_marker": "POST_HEAVY_HANDOFF_REACHED",
            "completion_marker": "POST_HEAVY_TAIL_COMPLETE",
            "resolved_symbols": ["run_post_heavy_tail"],
            "exact_outer_entrypoint": Path(__file__).is_file(),
            "heavy_handoff_reached": True,
            "post_heavy_tail_executed": True,
            "completion_path_reachable": True,
            "completion_receipt_written": True,
        }}
        (WORKING / "post-heavy-tail.json").write_text(json.dumps(receipt))
        print("POST_HEAVY_TAIL_COMPLETE")
    else:
        (WORKING / "run_receipt.json").write_text(
            json.dumps({{"status": "PASS", "completed_units": units}})
        )

def dependency_reexec_contract():
    source_path = Path(__file__).resolve()
    os.execve(sys.executable, [sys.executable, str(source_path)], os.environ.copy())

safety_mode = os.environ.get("SHIP_RUNTIME_SAFETY_PROBE")
if safety_mode:
    WORKING.mkdir(parents=True, exist_ok=True)
    if safety_mode == "late_tail":
        print("POST_HEAVY_HANDOFF_REACHED")
        run_post_heavy_tail(1, proof=True)
    elif safety_mode == "dynamic_module":
        import dataclasses
        import platform

        module_name = "ship_kaggle_selftest_embedded"
        module = types.ModuleType(module_name)
        module.__file__ = str(Path(__file__).resolve())
        sys.modules[module_name] = module
        registered_before_exec = sys.modules.get(module_name) is module
        exec(compile(EMBEDDED_SOURCE, module.__file__, "exec"), module.__dict__)
        payload = module.Payload(7)
        receipt = {{
            "status": "PASS", "completed_units": 1,
            "python_version": platform.python_version(),
            "registered_module_names": [module_name],
            "modules_registered_before_exec": registered_before_exec,
            "module_identity_preserved": sys.modules.get(module_name) is module,
            "dataclass_definition_loaded": dataclasses.is_dataclass(payload),
        }}
        (WORKING / "dynamic-module.json").write_text(json.dumps(receipt))
        print("DYNAMIC_MODULE_TARGET_MINOR_PROBE_PASS")
    elif safety_mode == "reexec":
        import platform

        entrypoint = Path(__file__).resolve()
        entrypoint_sha = hashlib.sha256(entrypoint.read_bytes()).hexdigest()
        token = hashlib.sha256(b"ship-kaggle-reexec-v1\\0" + entrypoint.read_bytes()).hexdigest()
        if os.environ.get("SHIP_REEXEC_CHILD") == "1":
            authenticated = os.environ.get("SHIP_REEXEC_TOKEN") == token
            child_receipt = {{
                "wrapper_reentered": True,
                "marker_authenticated": authenticated,
                "reentered_file_sha256": entrypoint_sha,
                "second_restart_refused": bool(authenticated),
            }}
            (WORKING / "reexec-child.json").write_text(json.dumps(child_receipt))
            print("WRAPPER_REEXEC_LIFECYCLE_CHILD_PASS")
            raise SystemExit(0)
        environment = os.environ.copy()
        environment["SHIP_REEXEC_CHILD"] = "1"
        environment["SHIP_REEXEC_TOKEN"] = token
        child = subprocess.run(
            [sys.executable, str(entrypoint)],
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        child_receipt = json.loads((WORKING / "reexec-child.json").read_text())
        receipt = {{
            "status": "PASS", "completed_units": 1,
            "python_version": platform.python_version(),
            "entrypoint_marker": "WRAPPER_REEXEC_LIFECYCLE_PASS",
            "reexec_module_name": "ship_kaggle_selftest_embedded",
            "initial_file_is_regular": entrypoint.is_file(),
            "initial_file_is_symlink": entrypoint.is_symlink(),
            "initial_file_sha256": entrypoint_sha,
            "dynamic_module_file_is_outer_entrypoint": True,
            "dynamic_module_file_is_regular": entrypoint.is_file(),
            "reexec_target_is_outer_entrypoint": child.returncode == 0,
            "completion_path_reachable": "run_receipt.json" in entrypoint.read_text(),
            **child_receipt,
        }}
        (WORKING / "reexec.json").write_text(json.dumps(receipt))
        print("WRAPPER_REEXEC_LIFECYCLE_PASS")
    elif safety_mode == "monitor":
        child = subprocess.Popen([sys.executable, "-c", "raise SystemExit(0)"])
        while child.poll() is None:
            time.sleep(0.001)
        returncode = child.wait()
        rss_missing = not (Path("/proc") / str(child.pid) / "status").exists()
        receipt = {{
            "status": "PASS", "completed_units": 1, "child_returncode": returncode,
            "child_reaped": True, "exit_observed_before_rss_error": True,
            "rss_unavailable_after_reap": rss_missing,
            "monitor_classification": "CHILD_EXITED_SUCCESS",
        }}
        (WORKING / "monitor.json").write_text(json.dumps(receipt))
        print("MONITOR_EXIT_PROBE_PASS")
    elif safety_mode == "linker":
        raw_linker = os.environ.get("LD_LIBRARY_PATH", "")
        receipt = {{
            "status": "PASS", "completed_units": 1, "strategy": "reconstructed",
            "raw_inherited_sha256": hashlib.sha256(raw_linker.encode()).hexdigest(),
            "final_components": [str(INPUT.resolve()), "/allowlisted/host"],
            "component_sources": ["authenticated_carrier", "allowlisted_host"],
            "component_exists": [True, True],
            "unsafe_components_used": False,
        }}
        (WORKING / "linker.json").write_text(json.dumps(receipt))
        print("LINKER_RECONSTRUCTION_PROBE_PASS")
    elif safety_mode == "diagnostics":
        child = subprocess.run(
            [sys.executable, "-c", "import sys; print('A'*300); print('B'*500, file=sys.stderr); raise SystemExit(17)"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        diagnostic_root = WORKING / "diagnostics"
        diagnostic_root.mkdir()
        records = {{}}
        for stream_name, data in (("stdout", child.stdout), ("stderr", child.stderr)):
            captured = data[-128:]
            path = diagnostic_root / (stream_name + ".tail")
            path.write_bytes(captured)
            records[stream_name] = {{
                "path": path.relative_to(WORKING).as_posix(), "total_bytes": len(data),
                "full_sha256": hashlib.sha256(data).hexdigest(),
                "captured_bytes": len(captured),
                "captured_sha256": hashlib.sha256(captured).hexdigest(),
                "truncated": len(data) > len(captured),
            }}
        receipt = {{
            "status": "PASS", "completed_units": 1, "child_returncode": child.returncode,
            "persisted_before_cleanup": True, **records,
        }}
        (WORKING / "diagnostic.json").write_text(json.dumps(receipt))
        print("CHILD_DIAGNOSTIC_PROBE_PASS")
    elif safety_mode == "media":
        def atom(name, payload):
            return (8 + len(payload)).to_bytes(4, "big") + name + payload
        video = WORKING / "probe.mp4"
        video.write_bytes(atom(b"ftyp", b"isom\\x00\\x00\\x00\\x00isom") + atom(b"mdat", b"synthetic") + atom(b"moov", b"proof"))
        receipt = {{
            "status": "PASS", "completed_units": 1,
            "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
            "decoded_frames": 3, "expected_frames": 3, "eof_reached": True,
            "decoder": "self-test target-like decoder",
        }}
        (WORKING / "probe.decode.json").write_text(json.dumps(receipt))
        print("MEDIA_FULL_DECODE_PROBE_PASS")
    else:
        raise KernelError("unknown safety probe")
    raise SystemExit(0)
units = int(os.environ["PREFLIGHT_UNITS"])
print("heavy_work_started")
time.sleep(0.002 * units)
run_post_heavy_tail(units)
print("stage_end")
'''
    entrypoint = kernel_dir / "script.py"
    entrypoint.write_text(source, encoding="utf-8")
    metadata = {
        "id": "demo/demo-pass",
        "title": "demo-pass",
        "code_file": "script.py",
        "kernel_type": "script",
        "enable_internet": False,
        "enable_gpu": False,
        "dataset_sources": ["demo/input"],
        "competition_sources": ["demo-competition"],
    }
    metadata_path = kernel_dir / "kernel-metadata.json"
    write_json(metadata_path, metadata)
    roundtrip_path = root / "roundtrip.json"
    write_json(
        roundtrip_path,
        {
            "schema": "celltrack-alpha.private-carrier-roundtrip.v1",
            "status": "PASS",
            "dataset_id": "demo/input",
            "dataset_version": 1,
            "expected_mount_root": "/kaggle/input/datasets/demo/input",
            "download_root": "input",
            "comparison": {
                "same_declared_paths": True,
                "same_declared_bytes": True,
                "same_declared_sha256": True,
                "raw_or_score_payload_present": False,
            },
        },
    )
    profile_path = root / "preflight.json"
    scenarios = []
    for role, units in (("tiny", 1), ("stratified", 2), ("stress", 4), ("expansive", 8)):
        scenarios.append(
            {
                "name": role,
                "role": role,
                "workload_units": units,
                "timeout_seconds": 5,
                "repeats": 2,
                "env": {"PREFLIGHT_UNITS": str(units)},
                "exit_codes": [0],
                "stdout_markers": ["STEP0_INVARIANTS_PASS", "stage_end"],
                "stderr_forbidden_markers": ["Traceback"],
                "required_outputs": [
                    {"path": "run_receipt.json", "kind": "json", "min_bytes": 10, "repeatability": "byte"},
                    {"path": "step0-invariants.json", "kind": "json", "repeatability": "byte"},
                ],
                "forbidden_outputs": ["submission.zip"],
                "completion": {
                    "path": "run_receipt.json",
                    "status_pointer": "/status",
                    "units_pointer": "/completed_units",
                    "success_values": ["PASS"],
                },
            }
        )

    def safety_probe(
        *,
        mode: str,
        marker: str,
        outputs: list[dict[str, Any]],
        completion_path: str,
        extra_env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        env = {"SHIP_RUNTIME_SAFETY_PROBE": mode}
        env.update(extra_env or {})
        return {
            "timeout_seconds": 5,
            "env": env,
            "exit_codes": [0],
            "stdout_markers": [marker],
            "stderr_forbidden_markers": ["Traceback"],
            "required_outputs": outputs,
            "forbidden_outputs": ["submission.zip"],
            "completion": {
                "path": completion_path,
                "status_pointer": "/status",
                "units_pointer": "/completed_units",
                "success_values": ["PASS"],
            },
        }

    monitor_probe = safety_probe(
        mode="monitor",
        marker="MONITOR_EXIT_PROBE_PASS",
        outputs=[{"path": "monitor.json", "kind": "json", "repeatability": "byte"}],
        completion_path="monitor.json",
    )
    late_tail_probe = safety_probe(
        mode="late_tail",
        marker="POST_HEAVY_TAIL_COMPLETE",
        outputs=[
            {"path": "post-heavy-tail.json", "kind": "json", "repeatability": "byte"}
        ],
        completion_path="post-heavy-tail.json",
    )
    late_tail_probe["stdout_markers"].insert(0, "POST_HEAVY_HANDOFF_REACHED")
    dynamic_module_probe = safety_probe(
        mode="dynamic_module",
        marker="DYNAMIC_MODULE_TARGET_MINOR_PROBE_PASS",
        outputs=[
            {"path": "dynamic-module.json", "kind": "json", "repeatability": "byte"}
        ],
        completion_path="dynamic-module.json",
    )
    reexec_probe = safety_probe(
        mode="reexec",
        marker="WRAPPER_REEXEC_LIFECYCLE_PASS",
        outputs=[{"path": "reexec.json", "kind": "json", "repeatability": "byte"}],
        completion_path="reexec.json",
    )
    linker_probes = [
        {
            **safety_probe(
                mode="linker",
                marker="LINKER_RECONSTRUCTION_PROBE_PASS",
                outputs=[{"path": "linker.json", "kind": "json", "repeatability": "byte"}],
                completion_path="linker.json",
                extra_env={"LD_LIBRARY_PATH": raw},
            ),
            "receipt_path": "linker.json",
        }
        for raw in ("", "/trusted:", "relative:/trusted")
    ]
    diagnostic_probe = safety_probe(
        mode="diagnostics",
        marker="CHILD_DIAGNOSTIC_PROBE_PASS",
        outputs=[
            {"path": "diagnostic.json", "kind": "json", "repeatability": "byte"},
            {"path": "diagnostics/stdout.tail", "kind": "file", "repeatability": "byte"},
            {"path": "diagnostics/stderr.tail", "kind": "file", "repeatability": "byte"},
        ],
        completion_path="diagnostic.json",
    )
    media_probe = safety_probe(
        mode="media",
        marker="MEDIA_FULL_DECODE_PROBE_PASS",
        outputs=[
            {
                "path": "probe.mp4",
                "kind": "mp4",
                "repeatability": "byte",
                "full_decode_receipt": "probe.decode.json",
            },
            {"path": "probe.decode.json", "kind": "json", "repeatability": "byte"},
        ],
        completion_path="probe.decode.json",
    )
    profile = {
        "schema": SCHEMA,
        "limits_file": "LMT.md",
        "kernel": {
            "directory": "kernel",
            "metadata_file": "kernel-metadata.json",
            "entrypoint": "script.py",
            "artifact_sha256": sha256_file(entrypoint),
            "metadata_sha256": sha256_file(metadata_path),
            "package_inventory_sha256": inventory_sha256(kernel_dir),
            "upload_transport": KAGGLE_CLI_SAVE_KERNEL_TRANSPORT,
            "command": ["{python}", "{entrypoint}"],
            "expected_metadata": metadata,
            "self_contained": True,
            "step0": {
                "assignment_marker": "STEP0 = run_step0()",
                "heavy_imports": ["numpy", "pandas", "torch", "zarr"],
                "heavy_work_marker": "heavy_work_started",
                "completion_marker": "STEP0_INVARIANTS_PASS",
                "receipt_path": "step0-invariants.json",
                "deterministic_invariants": [
                    "input_identity",
                    "inventory",
                    "path_topology",
                    "cardinality",
                ],
                "probe": {
                    "timeout_seconds": 5,
                    "env": {"SHIP_STEP0_ONLY": "1"},
                    "exit_codes": [0],
                    "stdout_markers": ["STEP0_INVARIANTS_PASS"],
                    "stderr_forbidden_markers": ["Traceback"],
                    "required_outputs": [{
                        "path": "step0-invariants.json",
                        "kind": "json",
                        "repeatability": "byte",
                    }],
                    "completion": {
                        "path": "step0-invariants.json",
                        "status_pointer": "/status",
                        "units_pointer": "/completed_units",
                        "success_values": ["PASS"],
                    },
                },
            },
            "execution_control_env": ["PREFLIGHT_UNITS"],
            "forbidden_source_fragments": [],
        },
        "mounts": [
            {
                "name": "input",
                "remote_root": "/kaggle/input/datasets/demo/input",
                "local_root": "input",
                "inventory_sha256": inventory_sha256(input_dir),
                "provider_layout": {
                    "source_type": "dataset",
                    "source_id": "demo/input",
                    "roundtrip_receipt": {
                        "path": "roundtrip.json",
                        "sha256": sha256_file(roundtrip_path),
                    }
                },
                "required_files": [{"path": "manifest.json", "bytes": manifest.stat().st_size, "sha256": manifest_sha}],
            },
            {
                "name": "competition",
                "remote_root": "/kaggle/input/competitions/demo-competition",
                "local_root": "competition_input",
                "inventory_sha256": inventory_sha256(competition_dir),
                "provider_layout": {
                    "source_type": "competition",
                    "source_id": "demo-competition"
                },
                "numeric_indexed_namespaces": [
                    raw_numeric_contract,
                    file_numeric_contract,
                ],
                "required_files": [{
                    "path": "sentinel.txt",
                    "bytes": competition_sentinel.stat().st_size,
                    "sha256": competition_sentinel_sha,
                }],
            }
        ],
        "scenarios": scenarios,
        "runtime": {
            "total_workload_units": 12,
            "remote_multiplier": 1.5,
            "fixed_remote_overhead_seconds": 0.1,
            "min_runs": 8,
            "min_distinct_workloads": 4,
            "max_relative_repeat_spread": 0.8,
            "min_largest_sample_fraction": 0.5,
            "memory_limit_bytes": 1073741824,
            "memory_remote_multiplier": 1.25,
            "calibration": [],
        },
        "adversarial": {
            "required": True,
            "faults": [
                "missing_mount",
                "missing_required_file",
                "corrupt_required_file",
                "duplicate_basename",
                "numeric_lexical_order",
                "numeric_missing_index",
                "numeric_extra_index",
                "numeric_alias_index",
            ],
            "failure_markers": ["KernelError", "FAIL_CLOSED", "Traceback"],
            "success_markers": ["stage_end"],
            "heavy_work_markers": ["heavy_work_started"],
        },
        "environment": {
            "python_version_prefix": f"{sys.version_info.major}.{sys.version_info.minor}",
            "required_imports": [],
            "carrier_provided_imports": [],
            "declared_release_imports": [],
            "release_dependency_probe": {},
        },
        "runtime_safety": {
            "post_heavy_tail": {
                "mode": "exact_outer_entrypoint_probe",
                "python_executable": "{python}",
                "python_version_prefix": f"{sys.version_info.major}.{sys.version_info.minor}",
                "entrypoint_marker": "POST_HEAVY_HANDOFF_REACHED",
                "completion_marker": "POST_HEAVY_TAIL_COMPLETE",
                "required_symbols": ["run_post_heavy_tail"],
                "receipt_path": "post-heavy-tail.json",
                "probe": late_tail_probe,
            },
            "dynamic_module_execution": {
                "mode": "registered_target_minor_probe",
                "python_executable": "{python}",
                "python_version_prefix": f"{sys.version_info.major}.{sys.version_info.minor}",
                "registered_module_names": ["ship_kaggle_selftest_embedded"],
                "receipt_path": "dynamic-module.json",
                "probe": dynamic_module_probe,
                "reexec_lifecycle": {
                    "mode": "outer_saved_script_reentry_probe",
                    "reexec_module_name": "ship_kaggle_selftest_embedded",
                    "entrypoint_marker": "WRAPPER_REEXEC_LIFECYCLE_PASS",
                    "receipt_path": "reexec.json",
                    "probe": reexec_probe,
                },
            },
            "subprocess_monitor": {
                "mode": "exit_reap_aware",
                "receipt_path": "monitor.json",
                "probe": monitor_probe,
            },
            "release_linker_environment": {
                "mode": "reconstructed",
                "inherited_variable": "LD_LIBRARY_PATH",
                "trusted_roots": [
                    {"path": "{mount:input}", "source": "authenticated_carrier"},
                    {"path": "/allowlisted/host", "source": "allowlisted_host"},
                ],
                "probes": linker_probes,
            },
            "child_diagnostics": {
                "mode": "durable_bounded",
                "max_capture_bytes": 128,
                "receipt_path": "diagnostic.json",
                "probe": diagnostic_probe,
            },
            "media": {
                "promised_mp4_outputs": ["probe.mp4"],
                "probe": media_probe,
            },
        },
        "secrets": ["KAGGLE_USERNAME", "KAGGLE_KEY"],
    }
    write_json(profile_path, profile)
    return profile_path, profile


def _selftest_runtime_safety_validators(root: Path) -> list[str]:
    checks: list[str] = []
    working = root / "runtime-safety-validator"
    working.mkdir()

    child = subprocess.Popen([sys.executable, "-c", "raise SystemExit(0)"])
    deadline = time.monotonic() + 5
    while child.poll() is None and time.monotonic() < deadline:
        time.sleep(0.001)
    if child.poll() != 0:
        raise AssertionError("synthetic monitor child did not exit successfully between polls")
    child_returncode = child.wait()
    rss_unavailable_after_reap = not Path(f"/proc/{child.pid}/status").exists()
    monitor_receipt = working / "monitor.json"
    write_json(
        monitor_receipt,
        {
            "status": "PASS",
            "completed_units": 1,
            "child_returncode": child_returncode,
            "child_reaped": True,
            "exit_observed_before_rss_error": True,
            "rss_unavailable_after_reap": rss_unavailable_after_reap,
            "monitor_classification": "CHILD_EXITED_SUCCESS",
        },
    )
    failures, _ = validate_runtime_safety_probe_output(
        working, {"kind": "subprocess_monitor", "receipt_path": "monitor.json"}
    )
    if failures:
        raise AssertionError(f"exit/reap-aware monitor validator rejected clean child exit: {failures}")
    checks.append("synthetic child exits between monitor polls and vanished VmRSS is not a resource fault")

    for index, raw in enumerate(("", "/trusted:", "relative:/trusted")):
        receipt = working / f"linker-{index}.json"
        write_json(
            receipt,
            {
                "status": "PASS",
                "completed_units": 1,
                "strategy": "reconstructed",
                "raw_inherited_sha256": sha256_bytes(raw.encode()),
                "final_components": ["/authenticated/carrier", "/allowlisted/host"],
                "component_sources": ["authenticated_carrier", "allowlisted_host"],
                "component_exists": [True, True],
                "unsafe_components_used": False,
            },
        )
        failures, _ = validate_runtime_safety_probe_output(
            working,
            {
                "kind": "release_linker_environment",
                "receipt_path": receipt.name,
                "raw_value": raw,
                "mode": "reconstructed",
                "trusted_roots": [
                    {"path": "/authenticated/carrier", "source": "authenticated_carrier"},
                    {"path": "/allowlisted/host", "source": "allowlisted_host"},
                ],
            },
        )
        if failures:
            raise AssertionError(f"safe linker reconstruction rejected for {raw!r}: {failures}")
    checks.append("empty, trailing-empty, and relative inherited linker components are discarded")

    diagnostic_root = working / "diagnostics"
    diagnostic_root.mkdir()
    full_streams = {"stdout": b"A" * 300, "stderr": b"B" * 500}
    stream_records: dict[str, Any] = {}
    for name, data in full_streams.items():
        captured = data[-128:]
        path = diagnostic_root / f"{name}.tail"
        path.write_bytes(captured)
        stream_records[name] = {
            "path": path.relative_to(working).as_posix(),
            "total_bytes": len(data),
            "full_sha256": sha256_bytes(data),
            "captured_bytes": len(captured),
            "captured_sha256": sha256_bytes(captured),
            "truncated": True,
        }
    write_json(
        working / "diagnostic.json",
        {
            "status": "PASS",
            "completed_units": 1,
            "child_returncode": 17,
            "persisted_before_cleanup": True,
            **stream_records,
        },
    )
    failures, _ = validate_runtime_safety_probe_output(
        working,
        {
            "kind": "child_diagnostics",
            "receipt_path": "diagnostic.json",
            "max_capture_bytes": 128,
        },
    )
    if failures:
        raise AssertionError(f"bounded durable diagnostic validator rejected proof: {failures}")
    checks.append("nonzero child diagnostics retain bounded streams, full hashes, and return code")

    def atom(name: bytes, payload: bytes) -> bytes:
        return (8 + len(payload)).to_bytes(4, "big") + name + payload

    video = working / "probe.mp4"
    video.write_bytes(
        atom(b"ftyp", b"isom\x00\x00\x00\x00isom")
        + atom(b"mdat", b"synthetic")
        + atom(b"moov", b"proof")
    )
    write_json(
        working / "probe.decode.json",
        {
            "status": "PASS",
            "video_sha256": sha256_file(video),
            "decoded_frames": 3,
            "expected_frames": 3,
            "eof_reached": True,
            "decoder": "self-test target-like decoder",
        },
    )
    failures, _ = validate_output(
        working,
        {
            "path": "probe.mp4",
            "kind": "mp4",
            "repeatability": "byte",
            "full_decode_receipt": "probe.decode.json",
        },
    )
    if failures:
        raise AssertionError(f"MP4 full-decode receipt validator rejected proof: {failures}")
    bad = load_json(working / "probe.decode.json")
    bad["decoded_frames"] = 2
    write_json(working / "probe.decode.json", bad)
    failures, _ = validate_output(
        working,
        {
            "path": "probe.mp4",
            "kind": "mp4",
            "repeatability": "byte",
            "full_decode_receipt": "probe.decode.json",
        },
    )
    if not failures:
        raise AssertionError("MP4 partial-decode frame drift was not rejected")
    checks.append("promised MP4 requires hash-bound full decode through expected frame count and EOF")
    return checks


def self_test() -> int:
    outcomes: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ship-kaggle-selftest-") as temp_name:
        root = Path(temp_name)
        outcomes.extend(_selftest_runtime_safety_validators(root))
        profile_path, base_profile = _fixture_profile(root)
        positive = certify(profile_path, root / "positive.json")
        if positive["status"] != "ELIGIBLE":
            raise AssertionError(f"positive fixture rejected: {positive}")
        fault_names = {run["fault"] for run in positive["adversarial_runs"] if run["status"] == "PASS"}
        if fault_names != set(base_profile["adversarial"]["faults"]):
            raise AssertionError("adversarial fixture coverage incomplete")
        raw_contract = base_profile["mounts"][1]["numeric_indexed_namespaces"][0]
        file_contract = base_profile["mounts"][1]["numeric_indexed_namespaces"][1]
        if not (
            raw_contract["entry_kind"] == "directory"
            and raw_contract["root_template"] == "train/{identity}.zarr/0/c"
            and len(raw_contract["identities"]) == 21
            and raw_contract["count"] == 100
            and file_contract["entry_kind"] == "file"
            and file_contract["relative_root"] == "numeric_files"
        ):
            raise AssertionError("numeric file/directory full-cardinality fixture drift")
        numeric_targets = {
            run["fault"]: run.get("numeric_fault_target")
            for run in positive["adversarial_runs"]
            if run["fault"] in (NUMERIC_NAMESPACE_FAIL_FAULTS | NUMERIC_NAMESPACE_PASS_FAULTS)
        }
        if any(
            not isinstance(target, dict)
            or target.get("namespace_id") != "raw_frames"
            or target.get("entry_kind") != "directory"
            or target.get("count") != 100
            for target in numeric_targets.values()
        ):
            raise AssertionError("numeric adversaries did not target the directory boundary")
        outcomes.append(
            "eligible positive binds direct files plus all 21x100 directory roots and directory adversaries"
        )

        def negative(
            name: str, mutate: Any, expected_status: str = "REJECTED"
        ) -> dict[str, Any]:
            case_root = root / name
            shutil.copytree(root / "kernel", case_root / "kernel")
            shutil.copytree(root / "input", case_root / "input")
            shutil.copytree(
                root / "competition_input", case_root / "competition_input"
            )
            shutil.copy2(root / "LMT.md", case_root / "LMT.md")
            shutil.copy2(root / "roundtrip.json", case_root / "roundtrip.json")
            profile = copy.deepcopy(base_profile)
            profile["kernel"]["directory"] = "kernel"
            profile["mounts"][0]["local_root"] = "input"
            mutate(case_root, profile)
            entry = case_root / "kernel" / "script.py"
            meta = case_root / "kernel" / "kernel-metadata.json"
            profile["kernel"]["artifact_sha256"] = sha256_file(entry)
            profile["kernel"]["metadata_sha256"] = sha256_file(meta)
            profile["kernel"]["package_inventory_sha256"] = inventory_sha256(case_root / "kernel")
            profile["mounts"][0]["inventory_sha256"] = inventory_sha256(case_root / "input")
            profile["mounts"][1]["inventory_sha256"] = inventory_sha256(
                case_root / "competition_input"
            )
            path = case_root / "profile.json"
            write_json(path, profile)
            result = certify(path, case_root / "receipt.json")
            if result["status"] != expected_status:
                raise AssertionError(
                    f"fixture {name} expected {expected_status}, observed {result['status']}"
                )
            outcomes.append(name)
            return result

        def dependency(case: Path, profile: dict[str, Any]) -> None:
            path = case / "kernel" / "script.py"
            source = path.read_text(encoding="utf-8")
            source = source.replace("units = int", "import definitely_missing_kaggle_dependency\nunits = int")
            path.write_text(source, encoding="utf-8")

        def function_local_dependency(case: Path, profile: dict[str, Any]) -> None:
            path = case / "kernel" / "script.py"
            source = path.read_text(encoding="utf-8")
            source = source.replace(
                "def run_step0():",
                "def run_step0():\n    import definitely_missing_function_local_dependency",
            )
            path.write_text(source, encoding="utf-8")

        def carrier_dependency_without_probe(_case: Path, profile: dict[str, Any]) -> None:
            profile["environment"]["carrier_provided_imports"] = ["zarr"]
            profile["environment"]["declared_release_imports"] = ["zarr"]
            profile["environment"]["release_dependency_probe"] = {}

        def unregistered_dynamic_module(case: Path, _profile: dict[str, Any]) -> None:
            path = case / "kernel" / "script.py"
            source = path.read_text(encoding="utf-8")
            source = source.replace("        sys.modules[module_name] = module\n", "", 1)
            path.write_text(source, encoding="utf-8")

        def missing_reexec_lifecycle(_case: Path, profile: dict[str, Any]) -> None:
            profile["runtime_safety"]["dynamic_module_execution"].pop(
                "reexec_lifecycle"
            )

        def synthetic_dynamic_reexec_file(case: Path, _profile: dict[str, Any]) -> None:
            path = case / "kernel" / "script.py"
            source = path.read_text(encoding="utf-8")
            source = source.replace(
                '"dynamic_module_file_is_outer_entrypoint": True,',
                '"dynamic_module_file_is_outer_entrypoint": False,',
                1,
            )
            path.write_text(source, encoding="utf-8")

        def child_only_reexec_bypass(case: Path, _profile: dict[str, Any]) -> None:
            path = case / "kernel" / "script.py"
            source = path.read_text(encoding="utf-8")
            source = source.replace(
                '"completion_path_reachable": "run_receipt.json" in entrypoint.read_text(),',
                '"completion_path_reachable": False,',
                1,
            )
            path.write_text(source, encoding="utf-8")

        def embedded_source_hash_drift(case: Path, _profile: dict[str, Any]) -> None:
            path = case / "kernel" / "script.py"
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            declared = None
            for node in tree.body:
                if (
                    isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == "EMBEDDED_SOURCE_SHA256"
                ):
                    declared = ast.literal_eval(node.value)
                    break
            if not isinstance(declared, str) or len(declared) != 64:
                raise AssertionError("self-test embedded source digest fixture drift")
            source = source.replace(f'"{declared}"', '"' + "0" * 64 + '"', 1)
            path.write_text(source, encoding="utf-8")

        def missing_runtime_safety_contract(_case: Path, profile: dict[str, Any]) -> None:
            profile.pop("runtime_safety")

        def missing_post_heavy_tail_contract(
            _case: Path, profile: dict[str, Any]
        ) -> None:
            profile["runtime_safety"].pop("post_heavy_tail")

        def unresolved_post_heavy_tail_symbol(
            _case: Path, profile: dict[str, Any]
        ) -> None:
            profile["runtime_safety"]["post_heavy_tail"]["required_symbols"] = [
                "missing_outer_tail_helper"
            ]

        def unproved_proc_rss_monitor(case: Path, profile: dict[str, Any]) -> None:
            profile["runtime_safety"]["subprocess_monitor"] = {"mode": "not_applicable"}
            path = case / "kernel" / "script.py"
            source = path.read_text(encoding="utf-8")
            source = source.replace(
                "import time",
                "import time\nimport subprocess\nMONITOR_STATUS = '/proc/{pid}/status'\ndef _monitor_api():\n    return subprocess.Popen([])",
            )
            path.write_text(source, encoding="utf-8")

        def unproved_linker_environment(case: Path, profile: dict[str, Any]) -> None:
            profile["runtime_safety"]["release_linker_environment"] = {"mode": "not_applicable"}
            path = case / "kernel" / "script.py"
            source = path.read_text(encoding="utf-8")
            source = source.replace(
                "STEP0 = run_step0()",
                "INHERITED_LINKER = os.environ.get('LD_LIBRARY_PATH', '')\nSTEP0 = run_step0()",
            )
            path.write_text(source, encoding="utf-8")

        def unproved_media_encode(case: Path, profile: dict[str, Any]) -> None:
            profile["runtime_safety"]["media"] = {"promised_mp4_outputs": []}
            path = case / "kernel" / "script.py"
            source = path.read_text(encoding="utf-8")
            source = source.replace(
                "STEP0 = run_step0()",
                "PROMISED_VIDEO = 'tracking.mp4'\nSTEP0 = run_step0()",
            )
            path.write_text(source, encoding="utf-8")

        def provider_mount_depth_drift(case: Path, profile: dict[str, Any]) -> None:
            receipt_path = case / "roundtrip.json"
            receipt = load_json(receipt_path)
            receipt["download_root"] = "input/nonexistent_inserted_child"
            write_json(receipt_path, receipt)
            profile["mounts"][0]["provider_layout"]["roundtrip_receipt"]["sha256"] = sha256_file(
                receipt_path
            )

        def false_legacy_short_provider_root(case: Path, profile: dict[str, Any]) -> None:
            legacy_root = "/kaggle/input/input"
            entrypoint = case / "kernel" / "script.py"
            entrypoint.write_text(
                entrypoint.read_text(encoding="utf-8").replace(
                    "/kaggle/input/datasets/demo/input", legacy_root
                ),
                encoding="utf-8",
            )
            receipt_path = case / "roundtrip.json"
            receipt = load_json(receipt_path)
            receipt["expected_mount_root"] = legacy_root
            write_json(receipt_path, receipt)
            profile["mounts"][0]["remote_root"] = legacy_root
            profile["mounts"][0]["provider_layout"]["roundtrip_receipt"]["sha256"] = sha256_file(
                receipt_path
            )

        def partial_competition_root_inverse(
            case: Path, _profile: dict[str, Any]
        ) -> None:
            entrypoint = case / "kernel" / "script.py"
            source = entrypoint.read_text(encoding="utf-8").replace(
                'COMPETITION_NAMESPACE = Path("/kaggle/input/competitions")',
                'COMPETITION_NAMESPACE = Path("/kaggle/input/competition")',
                1,
            )
            entrypoint.write_text(source, encoding="utf-8")

        def wrong_competition_root_inverse_order(
            case: Path, _profile: dict[str, Any]
        ) -> None:
            entrypoint = case / "kernel" / "script.py"
            source = entrypoint.read_text(encoding="utf-8").replace(
                'COMPETITION = Path("/kaggle/input/competitions/demo-competition")',
                'COMPETITION = Path("/kaggle/input/competitions/rewritten/demo-competition")',
                1,
            )
            entrypoint.write_text(source, encoding="utf-8")

        def missing_output(_case: Path, profile: dict[str, Any]) -> None:
            for scenario in profile["scenarios"]:
                scenario["required_outputs"].append({"path": "absent.json", "kind": "json", "repeatability": "none"})

        def broad(case: Path, profile: dict[str, Any]) -> None:
            path = case / "kernel" / "script.py"
            source = path.read_text(encoding="utf-8").replace("STEP0 = run_step0()", "_unused = list(INPUT.rglob(\"*\"))\nSTEP0 = run_step0()")
            path.write_text(source, encoding="utf-8")

        def ignored_control(case: Path, profile: dict[str, Any]) -> None:
            path = case / "kernel" / "script.py"
            source = path.read_text(encoding="utf-8").replace('units = int(os.environ["PREFLIGHT_UNITS"])', 'units = 1  # PREFLIGHT_UNITS intentionally ignored')
            path.write_text(source, encoding="utf-8")

        def lexical_numeric_order(case: Path, _profile: dict[str, Any]) -> None:
            path = case / "kernel" / "script.py"
            source = path.read_text(encoding="utf-8").replace(
                "        ordered_names = sorted(actual_names, key=int)",
                "        ordered_names = sorted(actual_names)",
                1,
            )
            path.write_text(source, encoding="utf-8")

        def step0_marker_after_heavy(case: Path, _profile: dict[str, Any]) -> None:
            path = case / "kernel" / "script.py"
            source = path.read_text(encoding="utf-8")
            source = source.replace(
                '    print("STEP0_INVARIANTS_PASS")\n    return {"ok": True}',
                '    return {"ok": True}',
                1,
            ).replace(
                'print("heavy_work_started")',
                'print("heavy_work_started")\nprint("STEP0_INVARIANTS_PASS")',
                1,
            )
            path.write_text(source, encoding="utf-8")

        def numeric_boundary_too_small(
            _case: Path, profile: dict[str, Any]
        ) -> None:
            profile["mounts"][1]["numeric_indexed_namespaces"][0]["count"] = 10

        def numeric_directory_declared_as_file(
            _case: Path, profile: dict[str, Any]
        ) -> None:
            profile["mounts"][1]["numeric_indexed_namespaces"][0][
                "entry_kind"
            ] = "file"

        def numeric_file_declared_as_directory(
            _case: Path, profile: dict[str, Any]
        ) -> None:
            profile["mounts"][1]["numeric_indexed_namespaces"][1][
                "entry_kind"
            ] = "directory"

        def numeric_duplicate_identity(
            _case: Path, profile: dict[str, Any]
        ) -> None:
            contract = profile["mounts"][1]["numeric_indexed_namespaces"][0]
            contract["identities"][1] = contract["identities"][0]

        def numeric_receipt_contract_drift(
            case: Path, _profile: dict[str, Any]
        ) -> None:
            path = case / "kernel" / "script.py"
            source = path.read_text(encoding="utf-8")
            marker = 'RAW_CONTRACT_SHA256 = "'
            start = source.index(marker) + len(marker)
            end = source.index('"', start)
            source = source[:start] + "0" * 64 + source[end:]
            path.write_text(source, encoding="utf-8")

        def mac_control_host_python(
            _case: Path, profile: dict[str, Any]
        ) -> None:
            profile["runtime_safety"]["post_heavy_tail"][
                "python_executable"
            ] = "/Users/agent/.local/bin/python3.12"

        def runtime(case: Path, profile: dict[str, Any]) -> None:
            _write_fixture_lmt(case, cap_hours=0.000001)
            profile["runtime"]["fixed_remote_overhead_seconds"] = 0.12

        def upload_omission(case: Path, profile: dict[str, Any]) -> None:
            entry = case / "kernel" / "script.py"
            sibling = case / "kernel" / "PACKAGE_MANIFEST.json"
            sibling.write_text('{"fixture":true}\n', encoding="utf-8")
            source = entry.read_text(encoding="utf-8")
            source = source.replace(
                "STEP0 = run_step0()",
                "_upload_only_probe = json.loads((Path(__file__).with_name('PACKAGE_MANIFEST.json')).read_text())\nSTEP0 = run_step0()",
                1,
            )
            entry.write_text(source, encoding="utf-8")

        negative("dependency rejection", dependency)
        negative("function-local dependency rejection", function_local_dependency)
        negative("carrier dependency without release probe rejection", carrier_dependency_without_probe)
        negative("unregistered target-minor dynamic module rejection", unregistered_dynamic_module)
        negative("missing dependency re-exec lifecycle rejection", missing_reexec_lifecycle)
        negative("synthetic dynamic-module reexec file rejection", synthetic_dynamic_reexec_file)
        negative("child-only reexec wrapper bypass rejection", child_only_reexec_bypass)
        negative("embedded source literal hash drift rejection", embedded_source_hash_drift)
        negative("missing runtime safety contract rejection", missing_runtime_safety_contract)
        negative("missing post-heavy outer-tail probe rejection", missing_post_heavy_tail_contract)
        negative("unresolved post-heavy outer-tail symbol rejection", unresolved_post_heavy_tail_symbol)
        negative("unproved proc RSS monitor rejection", unproved_proc_rss_monitor)
        negative("unproved linker environment rejection", unproved_linker_environment)
        negative("unproved MP4 encode rejection", unproved_media_encode)
        negative("provider mount-depth drift rejection", provider_mount_depth_drift)
        negative("false legacy short profile plus receipt root rejection", false_legacy_short_provider_root)
        negative("partial competition-root inverse rejection", partial_competition_root_inverse)
        negative(
            "wrong competition-root inverse order rejection",
            wrong_competition_root_inverse_order,
        )
        negative("missing output rejection", missing_output)
        negative("broad discovery rejection", broad)
        negative("ignored workload control rejection", ignored_control)
        negative("lexical numeric namespace order rejection", lexical_numeric_order)
        negative("Step0 completion after heavy-work rejection", step0_marker_after_heavy)
        negative("numeric namespace boundary underfit rejection", numeric_boundary_too_small)
        negative("numeric directory declared as file rejection", numeric_directory_declared_as_file)
        negative("numeric file declared as directory rejection", numeric_file_declared_as_directory)
        negative("numeric root-template duplicate identity rejection", numeric_duplicate_identity)
        negative("numeric Step0 receipt contract binding rejection", numeric_receipt_contract_drift)
        host_path_result = negative(
            "macOS control-host Python path pre-simulation rejection",
            mac_control_host_python,
        )
        if not (
            host_path_result["static"]["status"] == "FAIL"
            and host_path_result["host_path_provenance"]["status"] == "FAIL"
            and host_path_result["step0_preheavy_run"]["status"] == "NOT_RUN"
            and host_path_result["simulation_runs"] == []
            and host_path_result["runtime_safety_runs"] == []
            and host_path_result["adversarial_runs"] == []
        ):
            raise AssertionError(
                "control-host Python path was not rejected before every execution surface"
            )
        negative("Kaggle CLI sibling-package omission rejection", upload_omission)
        negative("runtime envelope requires approval at LMT cap", runtime, "APPROVAL_REQUIRED")
    print(json.dumps({"status": "PASS", "checks": outcomes}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init-profile", help="create a hash-bound adapter skeleton")
    init_parser.add_argument("--kernel-dir", type=Path, required=True)
    init_parser.add_argument("--output", type=Path, required=True)
    check_parser = subparsers.add_parser("check", help="validate a completed adapter without running it")
    check_parser.add_argument("--profile", type=Path, required=True)
    certify_parser = subparsers.add_parser("certify", help="run the complete simulator and emit a receipt")
    certify_parser.add_argument("--profile", type=Path, required=True)
    certify_parser.add_argument("--receipt", type=Path, required=True)
    subparsers.add_parser("self-test", help="run generated positive and negative fixtures")
    args = parser.parse_args()
    try:
        if args.command == "init-profile":
            profile = make_profile(args.kernel_dir.resolve(), args.output.resolve())
            print(json.dumps({"status": "PROFILE_CREATED", "path": str(args.output.resolve()), "profile_sha256": sha256_file(args.output.resolve()), "remaining": ["mounts", "scenarios", "runtime", "adversarial markers"]}, indent=2))
            return 0
        if args.command == "check":
            profile = load_json(args.profile.resolve())
            lmt_path, lmt_policy = profile_lmt(args.profile.resolve(), profile)
            result = validate_profile(args.profile.resolve(), profile, lmt_path, lmt_policy)
            payload = {"status": "PASS" if not result["failures"] else "FAIL", "failures": result["failures"], "warnings": result["warnings"]}
            print(json.dumps(payload, indent=2))
            return 0 if payload["status"] == "PASS" else 2
        if args.command == "certify":
            result = certify(args.profile.resolve(), args.receipt.resolve())
            print(json.dumps({"status": result["status"], "receipt": str(args.receipt.resolve()), "receipt_content_sha256": result["receipt_content_sha256"]}, indent=2))
            if result["eligible"]:
                return 0
            return 4 if result["status"] == "APPROVAL_REQUIRED" else 2
        return self_test()
    except CertifierError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, indent=2), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

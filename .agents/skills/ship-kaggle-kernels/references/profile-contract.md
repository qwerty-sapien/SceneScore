# Preflight profile contract

Schema: `ship-kaggle-kernels.profile.v1`. Paths are resolved relative to the profile file unless
absolute. Put the profile outside the kernel directory so its own receipt changes cannot alter the
package inventory hash.

`limits_file` is mandatory and must resolve to repository-root `LMT.md`. Certification binds its
SHA-256 and reads the autonomous Kaggle projection boundary from its machine policy block.

## Kernel

`kernel` requires:

- `directory`, `metadata_file`, and `entrypoint`;
- `artifact_sha256`, `metadata_sha256`, and `package_inventory_sha256`;
- `upload_transport: "kaggle-cli-save-kernel.v1"`. This is deliberately not
  configurable: Kaggle's CLI sends the declared script/notebook body and metadata,
  not arbitrary local siblings. Runtime code, manifests, checkpoints, and wheels must
  therefore be embedded in the entrypoint or arrive through declared Kaggle sources;
- an argv-only `command` using `{python}`, `{entrypoint}`, `{working}`, `{sandbox}`, or
  `{mount:NAME}` placeholders; shell strings are rejected;
- `expected_metadata`, an exact subset such as ID, title, `enable_internet`, `enable_gpu`, and
  source lists;
- `self_contained: true` to reject imported sibling Python files;
- `step0.assignment_marker`, `step0.heavy_imports`, and `step0.heavy_work_marker`;
- `step0.completion_marker`, `step0.receipt_path`, and an ordered unique
  `step0.deterministic_invariants` list containing at least `input_identity`, `inventory`,
  `path_topology`, and `cardinality`;
- `execution_control_env`, listing every environment key used to select a bounded workload; and
- optional `forbidden_source_fragments`.

All profile keys named `command`, `*_executable`, or `*_interpreter` are provenance checked before
simulation. Runtime Python fields should use `{python}`; an explicit interpreter must be an
absolute target-resolved executable. macOS `/Users/...`, local `/home/...`, Windows drive-letter,
and `~` paths fail static validation unless the value lies inside a canonical materialized Kaggle
root derived from metadata. `init-profile` emits `{python}` so a profile cannot freeze the control
host's interpreter path by accident.

For notebooks, declare an explicit noninteractive execution command. The simulator materializes
only the exact script/notebook that the Kaggle CLI uploads into a fresh source directory; it does
not copy the rest of the local kernel folder. It then rewrites only exact declared Kaggle roots in
that temporary entrypoint; the original bytes remain the certified bytes.

Every ordinary successful run must write the Step0 JSON receipt in the fresh working directory
before heavy work. Its `status` must be `PASS`; `invariants` must equal the profile's ordered list;
and `numeric_namespaces` must exactly cover every declared numeric namespace. The completion marker
must appear exactly once in stdout before the heavy-work marker, which must also appear exactly
once. Every scenario must require both the Step0 receipt as JSON output and the completion marker.
Injected deterministic faults must leave no Step0 receipt. This prevents a cheap raw-inventory,
path, or cardinality comparison from being deferred until after material computation.

## Mounts

Each mount requires a unique `name`, an absolute `remote_root` under `/kaggle/input`, a local
representative `local_root`, and its `inventory_sha256`. `required_files` may pin relative path,
byte count, and SHA-256. Mounts must map one-to-one onto the exact `dataset_sources` and
`competition_sources` in kernel metadata. The certifier independently derives Dataset roots as
`/kaggle/input/datasets/OWNER/SLUG` and competition roots as
`/kaggle/input/competitions/SLUG`; a profile cannot override either derivation. The simulator
copies inputs into those derived roots, not into self-asserted profile roots.

Every mount requires `provider_layout.source_type` (`dataset` or `competition`) and exact
`provider_layout.source_id`, matching one metadata source. Every Dataset mount also requires
`provider_layout.roundtrip_receipt` with repository-relative `path` and exact `sha256`. The
receipt must be `PASS`, prove identical declared paths/bytes/hashes with no raw/score payload,
bind the same `dataset_id`, and its `download_root` (or historical `downloaded_root`) must resolve
to the mount's exact `local_root`. Its authenticated `expected_mount_root` must equal the
metadata-derived canonical root. When remote
evidence supersedes only that historical mount assertion, add
`provider_layout.mount_layout_correction` with the exact correction path/SHA; the correction must
bind the superseded receipt hash and its `correct_expected_mount_root` must equal `remote_root`.
This prevents a local simulator from accepting either archive depth drift or a self-consistent
legacy short root that contradicts provider metadata. Competition mounts do not require a Dataset
round-trip receipt; their provider type/ID and canonical root remain mandatory.

When release code consumes a numeric-indexed direct-entry namespace, its mount adds
`numeric_indexed_namespaces`. Each contract requires a globally unique `id`, explicit
`entry_kind` (`file` or `directory`), a basename-only `filename_template` containing `{index}`
exactly once, nonnegative `first_index`, and `count`. It declares exactly one root mode:

- `relative_root` for one namespace; or
- `root_template` containing `{identity}` exactly once plus a nonempty, ordered, unique
  `identities` list. The certifier expands and validates every identity/root pair independently.

All roots are relative to that mount, path-safe, and exclusive across expanded contracts. `count`
must be at least 10, and generated canonical names must actually have a different lexical and
numeric order; `0..9` alone is not a valid boundary fixture. Every expanded local root must contain
exactly those direct regular files or direct real directories according to `entry_kind`; mixing
kinds, aliases, extras, missing names, and symlinks fails closed.

The Step0 receipt's `numeric_namespaces` object must exactly cover the declared IDs. Each ID record
binds `contract_sha256`, `entry_kind`, `count`, and an ordered `instances` list. Every instance
binds its `identity` (`null` for `relative_root`), expanded `relative_root`, `count`, and exact
canonical numeric `ordered_names`. This binds all identity-expanded roots rather than only one
representative. Numeric namespaces require `numeric_lexical_order`, `numeric_missing_index`,
`numeric_extra_index`, and `numeric_alias_index` adversaries. The certifier injects those faults
against a declared full-cardinality namespace while preserving file and directory semantics.

The inventory digest is SHA-256 of canonical JSON records sorted by path, where each record is
`{"bytes": N, "path": "relative/name", "sha256": "..."}`. The certifier generates it in
`init-profile` when a mirror already exists.

## Scenarios

Certification requires all roles: `tiny`, `stratified`, `stress`, and `expansive`. Each scenario
declares:

- unique `name` and one required `role`;
- positive `workload_units`, `timeout_seconds`, and `repeats >= 2`;
- `env` containing at least one declared execution-control key;
- `stdout_markers` and optional `stderr_forbidden_markers`;
- `required_outputs`, each with a relative `path`, `kind` (`file`, `json`, `jsonl`, `csv`, or
  `zip`; use `mp4` for videos), `repeatability` (`byte` or `none`), and optional
  size/hash/row/header assertions; and
- `completion`, naming a JSON output plus JSON pointers for status and completed work units.

The completion unit must exactly equal `workload_units`; this prevents an ignored subsampling flag
from making a fast but meaningless test pass.

Every `.mp4` required output must use `kind: "mp4"` and name a `full_decode_receipt`. The receipt
must be a JSON object with `status: "PASS"`, the exact `video_sha256`, positive equal
`decoded_frames`/`expected_frames`, `eof_reached: true`, and a nonempty `decoder` identity. The
certifier also walks the ISO-BMFF top-level atoms and requires `ftyp`, `mdat`, and `moov`. Opening a
writer, checking nonzero bytes, decoding only the first frame, or trusting a receipt for different
video bytes is insufficient.

At least one semantic output per scenario must be byte-repeatable. Repeated runs and the
duplicate-basename mutation must preserve that hash. Mark timing/log receipts `none` and keep the
substantive bounded result in a separate deterministic artifact when necessary.

The four roles must be observation-distinct. `stratified` covers every known input class;
`stress` concentrates slow/large/boundary cases; `expansive` is the largest locally practical
bounded sample. Do not define four names around the same data.

## Runtime

`runtime` requires:

- `total_workload_units`, `remote_multiplier`, and `fixed_remote_overhead_seconds`;
- `min_runs`, `min_distinct_workloads`, `max_relative_repeat_spread`, and
  `min_largest_sample_fraction`; and
- physical `memory_limit_bytes` and `memory_remote_multiplier`; and
- `calibration`, a list of matched positive `local_seconds`/`remote_seconds` observations.

The certifier measures child peak RSS, fits a conservative multi-scale envelope, and rejects
missing measurements or a projection above physical memory capacity. It emits `ELIGIBLE` only
strictly below the LMT runtime boundary and `APPROVAL_REQUIRED` at or above it. Profiles containing
retired `hard_limit_seconds`, `max_eligible_fraction`, or `max_eligible_memory_fraction` keys fail.

## Adversarial contract

`adversarial.required` must be true. Select applicable faults from `missing_mount`,
`missing_required_file`, `corrupt_required_file`, and `duplicate_basename`. Declare failure
markers and success/heavy-work markers. Every injected fault must return nonzero or time out, show
a failure marker, omit the completion receipt, and avoid all heavy/success markers.

## Environment and secrets

`environment` can require a Python major/minor prefix and must classify the complete third-party
release import surface, including imports nested inside functions:

- `required_imports`: modules supplied by the base runtime; each must import in the local simulator;
- `carrier_provided_imports`: modules supplied by declared Kaggle input carriers;
- `declared_release_imports`: the exact union of those two provider lists; and
- `release_dependency_probe`: an object with a literal `stdout_marker` required by every scenario
  and `carrier_mounts` naming the mounts that supply carrier imports.

The entrypoint must run the dependency-only probe before model loading, competition-data access,
or heavy work. A profile is rejected when an AST-discovered third-party import is undeclared, a
module has two providers, a carrier mount is unknown, or any scenario omits the probe marker. The
simulator adds a `sitecustomize.py` that denies Python socket connections, removes declared secret
variables, sets offline package-manager flags, and provides no Kaggle credentials.

## Runtime safety

`runtime_safety` is mandatory. The certifier detects subprocess APIs, `/proc` resource reads,
dynamic-linker variables, and MP4 release paths anywhere in the exact entrypoint. `not_applicable`
is accepted only when the corresponding release path is absent.

Each applicable `probe` is a target-like invocation of the exact script-only materialization in a
fresh simulator. It declares `timeout_seconds`, a nonempty string `env` control mapping that is
literal in the source, `exit_codes`, `stdout_markers`, `required_outputs`, and a JSON `completion`
receipt. The certifier assigns probe workload unit `1`, runs probes outside runtime projection, and
records them in `runtime_safety_runs`. A declared probe that is not executed successfully makes the
focused pre-push debug fail.

### Exact post-heavy outer tail

`runtime_safety.post_heavy_tail` is mandatory for every release. Set `mode` to
`exact_outer_entrypoint_probe` and declare:

- an executable `python_executable` plus its exact major/minor `python_version_prefix`;
- literal `entrypoint_marker` and `completion_marker` strings emitted after the representative
  heavy-stage handoff and after final output/evidence creation;
- nonempty, unique `required_symbols` naming every top-level outer helper used only after the
  heavy-stage handoff;
- `receipt_path`; and
- a target-like `probe` using the ordinary exact script-only outer entrypoint.

The certifier rejects a required symbol that is not top-level-defined in the transmitted script.
The receipt must have `status: "PASS"`, `completed_units: 1`, the exact target Python version,
the exact two markers and symbol list, and set `exact_outer_entrypoint`, `heavy_handoff_reached`,
`post_heavy_tail_executed`, `completion_path_reachable`, and `completion_receipt_written` to true.
The probe must use representative heavy-stage artifacts and invoke the same finalizer used by the
normal provider path. A compile-only check, early-exit branch, retyped tail, embedded-child-only
probe, or self-consistent receipt that does not run the finalizer is invalid.

### Target-minor dynamic module execution

When the exact entrypoint contains a dynamic `exec`, `dynamic_module_execution.mode` must be
`registered_target_minor_probe`. Declare the exact `registered_module_names`, an executable
`python_executable`, a major/minor `python_version_prefix`, a `receipt_path`, and a target-like
`probe`. The script-only release path must create each embedded module with `types.ModuleType`,
insert it into `sys.modules` before `exec`, and execute the exact embedded byte string in the
module dictionary. This is mandatory even when the development interpreter happens to load the
source successfully.

The receipt must contain `status: "PASS"`, `completed_units: 1`, the exact interpreter version and
module-name list, plus `modules_registered_before_exec`, `module_identity_preserved`, and
`dataclass_definition_loaded` all set to `true`. Project adapters should also bind exact embedded
source hashes in their semantic receipt. A retyped dataclass toy, a post-`exec` registration, or a
test-only helper that differs from the released loader does not certify the package.

### Dependency re-exec lifecycle

When the exact entrypoint or an embedded source contains `os.execve` driven by
`Path(__file__).resolve()`, add `dynamic_module_execution.reexec_lifecycle` with mode
`outer_saved_script_reentry_probe`, the exact registered `reexec_module_name`, a literal
`entrypoint_marker`, `receipt_path`, and a target-minor `probe`.

The receipt must prove `initial_file_is_regular`, `dynamic_module_file_is_outer_entrypoint`,
`dynamic_module_file_is_regular`, `reexec_target_is_outer_entrypoint`, `wrapper_reentered`,
`marker_authenticated`, `completion_path_reachable`, and `second_restart_refused` are true;
`initial_file_is_symlink` must be false. It must bind the target Python version, module name,
entrypoint marker, and pre/post file hashes. This prevents a successful dependency install from
masking a restart into a nonexistent synthetic path or into an embedded child that bypasses the
outer wrapper's completion and evidence paths.

### Exit/reap-aware subprocess monitors

When a subprocess plus `/proc`/`VmRSS` read is detected, `subprocess_monitor.mode` must be
`exit_reap_aware`, with `receipt_path` and `probe`. The synthetic probe must arrange for a child to
exit successfully between monitor polls and persist:

```json
{
  "status": "PASS",
  "completed_units": 1,
  "child_returncode": 0,
  "child_reaped": true,
  "exit_observed_before_rss_error": true,
  "rss_unavailable_after_reap": true,
  "monitor_classification": "CHILD_EXITED_SUCCESS"
}
```

The release monitor must poll/reap before treating a missing `/proc/<pid>/status` or `VmRSS` as a
monitor failure. A successful child exit may not be relabeled as a resource fault solely because
process accounting vanished after exit.

### Release linker environment

When `LD_LIBRARY_PATH`, `LD_PRELOAD`, `LD_AUDIT`, `LD_DEBUG`, or `LD_DEBUG_OUTPUT` is reachable in
the source, `release_linker_environment.mode` must be `reconstructed` or `target_like_probe`, and
`inherited_variable` must be `LD_LIBRARY_PATH`. `trusted_roots` must include at least one
`authenticated_carrier` mount-bound path (use `{mount:NAME}`) and one normalized absolute
`allowlisted_host` path. The probe list must include at least:

- an exactly empty inherited value;
- a leading, trailing, or doubled empty component; and
- a relative component.

Every probe receipt binds `raw_inherited_sha256`, the chosen `strategy`,
`unsafe_components_used: false`, and parallel `final_components`/`component_sources` lists. Final
components must be unique, normalized absolute paths, parallel `component_exists` values must all
be true, and each component must remain within a declared root of its source. Each source must be
`authenticated_carrier` or `allowlisted_host`. Empty/current-directory, relative, newline-bearing,
duplicate, arbitrary mounted, or otherwise untrusted inherited components cannot survive into the
child. Prefer deterministic reconstruction from authenticated carrier libraries plus a physically
verified host-driver allowlist; a target-like mode still has to prove the same safe final list for
every injected spelling.

### Durable bounded child diagnostics

Any detected release subprocess requires `child_diagnostics.mode: "durable_bounded"`, a positive
`max_capture_bytes` no greater than 1 MiB, `receipt_path`, and a forced-failure `probe`. The probe
must preserve a nonzero `child_returncode`, set `persisted_before_cleanup: true`, and provide
`stdout` and `stderr` records with:

- a relative durable path under the working directory;
- `total_bytes` and `full_sha256` for the complete stream;
- `captured_bytes` and `captured_sha256` for the bounded persisted copy; and
- a truncation flag exactly consistent with the two byte counts.

The certifier re-hashes each bounded copy and enforces the cap. Temporary `/tmp` logs or diagnostics
written only after cleanup begins do not satisfy the contract.

### Promised MP4 inventory

When an MP4 encode/path is detected, `media.promised_mp4_outputs` must list every promised relative
MP4 exactly once and `media.probe` must declare exactly that set as `kind: "mp4"` required outputs.
The fresh probe working directory may contain no undeclared MP4. Each MP4 is then subject to the
full-decode receipt contract above.

## Receipt interpretation

`ELIGIBLE` means every required check passed for the exact recorded hashes. `REJECTED` is the only
other certification outcome. The receipt also records unmodeled risks; any risk material to this
kernel is a human/agent adversarial-review rejection even if all automated checks passed.

# Kaggle failure taxonomy

Use the narrowest stable class. Preserve the original stderr/stdout excerpt and artifact hashes.
An unchanged class plus unchanged causal inputs is not a new experiment.

| Class | Typical evidence | Required prevention |
|---|---|---|
| `PACKAGE_OMISSION` | Missing entrypoint, sibling module, checkpoint, wheel, or manifest | Reproduce Kaggle CLI's script/notebook-only materialization; whole-package inventory hash; self-contained import probe; required-file pins |
| `MOUNT_IDENTITY` | Zero/ambiguous content matches, wrong private mount, provider archive flattening/nesting, legacy short root, source drift | Derive canonical owner-qualified Dataset/competition roots independently from exact metadata; require one-to-one provider source/mount provenance; stage the simulator only at derived roots; require immutable carriers, per-mount inventories, and byte-bound Dataset round-trip path-depth parity (or an independently hash-bound layout correction) |
| `BROAD_DISCOVERY` | `rglob`, `os.walk`, `glob("**")`, wrong duplicate selected | Exact roots and filenames; inject duplicate basename and require fail-closed behavior |
| `DEPENDENCY_OFFLINE` | `ModuleNotFoundError`, ABI mismatch, undeclared network install | Offline release-path import/decode run; wheel hash and environment fingerprint |
| `DYNAMIC_MODULE_IDENTITY` | Dataclass/class definition fails because embedded source executes in a bare namespace or under a different Python minor than the provider | Execute the exact embedded bytes under the target Python; create `ModuleType`, register in `sys.modules` before `exec`, bind source hash/module identity, and require a dataclass-load receipt |
| `EMBEDDED_SOURCE_HASH_DRIFT` | A repaired embedded literal is executed while its inherited `*_SOURCE_SHA256` still names predecessor bytes; side-channel roles pass but normal provider `main()` rejects | Recompute every top-level paired `*_SOURCE`/`*_SOURCE_SHA256` literal during static certification and execute the normal entrypoint hash assertion before release |
| `DEPENDENCY_REEXEC_LIFECYCLE` | Offline install succeeds, then restart rejects a nonexistent/symlink `__file__`, or re-executes an embedded child that skips wrapper completion/evidence | Bind dynamic-module `__file__` to the real outer saved script; target-minor probe the authenticated restart, wrapper re-entry, single-restart guard, and retained completion path |
| `LINKER_ENVIRONMENT` | Child aborts on inherited linker spelling; empty/relative component admits CWD; arbitrary host/mount library precedes pinned carrier | Reconstruct only from authenticated carrier plus verified host allowlist, or execute target-like probes for exact empty, leading/trailing/doubled-empty, and relative inherited values; bind raw-value hash and trusted final-component provenance |
| `STEP0_ORDER` | Heavy work begins before input identity, complete raw inventory, path topology, cardinality, or numeric ordering is authenticated; a late cheap gate fails after expensive work | Pure-stdlib Step0 receipt covering all deterministic invariants; full-cardinality file/directory numeric boundary fixtures whose lexical/numeric orders differ; expand and bind every identity-templated root; prove receipt and completion marker before heavy work; missing/extra/alias index adversaries fail with no Step0 receipt |
| `CONTROL_HOST_PATH_LEAK` | A frozen runtime-safety probe or command names a developer-host interpreter such as `/Users/.../python3.12`, so certification aborts before simulations on another host | Statically provenance-check command/executable/interpreter fields; use `{python}` or an executable target-resolved path; reject `/Users`, local `/home`, drive-letter, and `~` paths before Step0 or simulation unless they lie inside a metadata-derived materialized root |
| `SUBPROCESS_MONITOR_RACE` | Child return code is `0`, then `/proc/<pid>/status`/`VmRSS` disappears and parent emits resource-monitor abort | Poll/reap before classifying missing process accounting; synthetic child-successfully-exits-between-polls target-like probe and typed receipt |
| `CHILD_DIAGNOSTIC_LOSS` | Platform child fails, but stdout/stderr lived only in `/tmp` or were deleted in outer cleanup; generic wrapper marker hides cause | Before cleanup, durably persist nonzero return code, total byte counts, full-stream hashes, and bounded stdout/stderr tails under the output root; force and validate the failure path |
| `OUTPUT_CONTRACT` | Complete status but absent, blank, stale, malformed, or wrong-root output | Fresh working dir; semantic completion receipt; recursive declared inventory |
| `MEDIA_DECODE` | MP4 writer opens/nonzero file exists, but stream is truncated, unreadable after first frame, has frame-count drift, or receipt binds another file | Exact promised-MP4 inventory; ISO-BMFF structure check; full decode through positive expected frame count and EOF; decoder identity and actual video SHA in receipt |
| `METADATA_DRIFT` | Title/ID mismatch, invalid Dataset-title length, missing privacy declaration, wrong GPU/internet/source flags | Before any Dataset-create subprocess, require a 6..50-character title, owner/slug ID, boolean privacy declaration, expected-ID equality, and bind the metadata hash; for kernels, require exact metadata hash/key equality and a normalized slug check |
| `FRESHNESS_RACE` | Existing slug, wrong exact version, receipt reused, concurrent push | Under-lock status, one-shot receipt, exact package re-hash, serial launcher |
| `RUNTIME_ENVELOPE` | Projection/timeout or high timing variance | Multi-scale repeated probe, slow-stratum sample, calibrated inflation, LMT disposition |
| `REMOTE_EXTERNAL` | Kaggle outage, scheduler/host loss, service fault | Preserve evidence; retry only under project policy; do not weaken local checks |

## Repository examples: evidence, not requirements

These examples explain why the generic checks exist. Do not copy their cell-tracking constants
into another project's adapter.

Positive patterns in the current repository:

- A dedicated immutable input carrier plus exact direct-manifest Step 0 prevented a mutable shared
  dataset from silently presenting another lane's files.
- Offline wheel installation followed by a release-path import showed that packaging and dependency
  transport were valid before heavy computation.
- Exact metadata/code/contract hashing and one-shot launch predicates prevent a receipt from being
  transferred to new bytes.

Negative regressions represented by the taxonomy:

- `ModuleNotFoundError: zarr` and missing sibling modules demonstrate that a development-machine
  import is not an offline Kaggle import proof.
- A test helper registered a dynamically executed dataclass module in `sys.modules`, while the
  released script executed identical bytes in a plain dictionary. Python 3.12 then failed inside
  `dataclasses` before model execution. This is `DYNAMIC_MODULE_IDENTITY`, not model evidence.
- A script that read a locally adjacent `PACKAGE_MANIFEST.json` passed a full-directory simulator
  but failed remotely because `kaggle kernels push` sends only the script body and metadata. Treat
  every local sibling as absent unless it is an explicitly declared Kaggle input source or embedded
  in the entrypoint; the certifier's automatic focused pre-push release debug enforces this.
- Recursive input traversal and ambiguous content lookup selected or scanned the wrong carrier.
- A successful native child returned `0`; after it was reaped, `/proc/<pid>/status` vanished and an
  outer monitor incorrectly emitted a resource abort. The model result was hidden by a
  `SUBPROCESS_MONITOR_RACE`, not disproven.
- A legacy runtime rejected a provider-supplied `LD_LIBRARY_PATH` spelling before child launch.
  Validate trusted library provenance rather than arbitrary inherited syntax, and preserve the next
  child failure's bounded diagnostics before deleting temporary runtime state.
- A repaired kernel authenticated its 43-file carrier and installed its wheels, but a later remote
  projection reached `1.062656 h` against a now-superseded `1.0 h` lane guard. The stop was
  historically correct under that package; future authority comes only from repository `LMT.md`.
- Post-failure `mistune` and `nbconvert` warnings are conversion noise, not the causal kernel class.

## Triage order

1. Find the first application traceback or fail-closed event. Ignore later notebook-conversion noise.
2. Determine whether heavy work started.
3. Bind the log to exact kernel version and package hashes.
4. Reproduce with the smallest scenario that retains the signature.
5. Add an adversarial fixture, make one causal repair, and replay all scenarios.

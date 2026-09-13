---
name: ship-kaggle-kernels
description: Certify Kaggle kernels before one-shot submission and validate Kaggle Dataset-create metadata before external mutation. Bind repository LMT.md, simulate Kaggle's filesystem and offline runtime locally, exercise a subsample-to-stress ladder, project runtime and memory, validate outputs, and inject common launch faults. Use whenever creating or releasing a Kaggle Dataset carrier, or creating, repairing, reviewing, or autonomously submitting a Kaggle kernel or notebook, especially after metadata, packaging, mount, dependency, output, freshness, or runtime failures.
---

# Ship Kaggle Kernels

## Purpose

Eliminate preventable Kaggle launch failures before spending a remote version. Build a thin
project adapter around the exact kernel bytes, then run a fail-closed local certification loop.
The certificate covers packaging, mounts, offline dependencies, execution controls, output
semantics, and the runtime envelope under repository `LMT.md`. It cannot guarantee against Kaggle service,
hardware, or scheduler faults that no local simulator can reproduce.

## Non-negotiable launch rule

Do not push autonomously unless `kaggle_kernel_certifier.py certify` emits `status: ELIGIBLE`
for the exact package, metadata, and `LMT.md` hashes being pushed. The receipt must include a
passing, automatically triggered `focused_pre_push_release_debug` result. `APPROVAL_REQUIRED` is
not autonomous authority. A prior receipt, partial pass, successful import, or single happy-path
run is not transferable evidence.

Never weaken a check just to turn a failure green. Repair the kernel or adapter, add the failure
as a regression, and replay the entire ladder. Preserve project governance, version freshness,
serial launch locks, quota accounting, and any human approval gates in addition to this skill.

For a Kaggle Dataset create, run the repository's bounded launcher rather than the CLI directly.
It must parse `dataset-metadata.json` and reject before starting any external process unless the
title is a trimmed 6..50-character string, `id` is an `owner/slug`, `isPrivate` is explicitly
boolean, and any caller-bound Dataset ID matches the metadata. A successful receipt must bind the
metadata hash and validated fields. This gate is independent of kernel certification and must not
change kernel-operation behavior.

## Workflow

### 1. Read project authority and classify the last failure

Read repository `LMT.md`, instructions, live state, launch receipts, kernel logs, and guards.
Classify the incident using [failure-taxonomy.md](references/failure-taxonomy.md). Separate:

- deterministic/preventable faults: package, mount, dependency, import order, path, output,
  freshness, or optimistic runtime projection;
- correct fail-closed resource stops; and
- rare external faults: Kaggle outage, host failure, scheduler loss, or timeout despite a
  certified envelope.

Do not resubmit an unchanged error signature.

### 2. Create one project adapter

Generate a profile beside, not inside, the kernel package:

```bash
python3 scripts/kaggle_kernel_certifier.py init-profile \
  --kernel-dir /absolute/path/to/kernel \
  --output /absolute/path/to/preflight-profile.json
```

Complete the profile using [profile-contract.md](references/profile-contract.md). Keep the skill
project-agnostic; all dataset roots, hashes, workload controls, semantic receipts, time limits,
and launch policy belong in the adapter.

The adapter must bind:

- the repository-root `LMT.md` path and hash;
- exact package, entrypoint, metadata, and local input-mirror inventories;
- exact remote mount roots and literal rewrites used only inside the temporary simulator;
- a one-to-one mapping from every metadata Dataset/competition source to its independently
  derived canonical Kaggle root, plus provider provenance for every release asset mount;
- every overlapping path rewrite that the simulator may apply to that root, including the
  owner-qualified competition root and the generic `/kaggle/input/competitions` prefix, with a
  fixed most-specific-to-least-specific application order and an exact inverse order;
- exact provider-downloaded topology for every Dataset carrier, binding the byte-perfect
  round-trip receipt and any separately authenticated mount-layout correction;
- host-path provenance for every profile command, executable, and interpreter: use runtime
  placeholders such as `{python}` or an exact target-resolved absolute path, and reject macOS
  `/Users/...`, local `/home/...`, Windows drive-letter, or `~` paths before any simulation unless
  the path is inside an independently derived materialized Kaggle root;
- target-like runtime-safety probes whenever release code launches child processes, reads
  `/proc` resource data, constructs a dynamic-linker environment, or encodes MP4s;
- an exact outer-entrypoint, target-minor post-heavy-tail probe that crosses the real heavy-work
  handoff and executes final output/evidence code with representative artifacts;
- four observation-distinct roles: `tiny`, `stratified`, `stress`, and `expansive`;
- an environment control for each workload and an output completion receipt proving the control
  was honored;
- a Step0 deterministic-invariant receipt covering input identity, complete inventory, path
  topology, and cardinality, plus a unique completion marker that every successful ladder run
  must emit before the heavy-work marker;
- every numeric-indexed direct-entry namespace used by release code, with explicit file/directory
  entry kind, either one exclusive relative root or one identity-expanded root template, canonical
  filename template, first index, and full expected cardinality; every expanded local boundary
  must contain at least 10 names and actually distinguish lexical from numeric ordering;
- required outputs and semantic assertions; and
- total work units, matched local/remote timing calibration when available, remote platform
  memory capacity, and a conservative whole-run projection.

Declare every third-party import reachable anywhere in the release entrypoint, including imports
inside functions. Split them between base-runtime imports that the simulator must import locally
and carrier-provided imports bound to explicit Kaggle mounts. Require one dependency-only release
probe before model loading, competition-data access, or heavy work in every scenario. The probe
must import the exact declared closure from the materialized script-only package and carrier
mounts, print its bound marker, and fail closed on a missing module or ABI/load error. A preflight
branch that skips function-local release imports is not certification evidence.

If the entrypoint dynamically executes embedded Python source, the adapter must additionally run
that exact embedded byte string under the target Python major/minor before release. Each synthetic
module must be created with `types.ModuleType`, inserted into `sys.modules` under the same frozen
name before `exec`, and retain identity through dataclass/class/function definition. A plain
dictionary namespace, a controller-Python-only unit test, or a retyped toy snippet is not valid
evidence. The probe receipt must bind the target interpreter, registered module names, exact
embedded-source hashes, and successful dataclass definition/loading before heavy work.
For every top-level literal `*_SOURCE` paired with `*_SOURCE_SHA256`, the certifier must also
recompute the digest from the exact UTF-8 bytes and reject any mismatch. The normal provider
entrypoint's own embedded-source assertion must be exercised before release; a side-channel role
probe alone is insufficient.

If the entrypoint or any embedded source re-executes `Path(__file__).resolve()` after an offline
dependency install, require a target-minor saved-script re-entry probe. The dynamic module's
`__file__` must be Kaggle's real regular outer entrypoint, not a synthetic working path. The
authenticated restart must target that same outer script so wrapper Step 0, completion handling,
diagnostics, and evidence sealing remain reachable. Materializing and restarting an embedded child
is invalid when it bypasses those wrapper stages. See [reexec-lifecycle.md](references/reexec-lifecycle.md).

Every release must also declare `runtime_safety.post_heavy_tail`. Run the exact materialized outer
entrypoint under the target Python major/minor with a bounded representative heavy-stage handoff;
then execute the same final output/evidence function used by the normal path. Bind every outer
symbol that the late tail requires, require handoff and terminal markers in stdout, and write a
receipt proving that the exact outer entrypoint, handoff, tail, completion path, and completion
receipt were reached. Compilation, AST inspection, an early-exit role, or a surrogate child that
never returns to the outer tail is not release evidence.

Prefer a small representative mirror over the full dataset. It must include the rarest and
costliest strata, boundary files, dependency wheels, and exact manifest structure used remotely.

### 3. Run the refinement loop

Run:

```bash
python3 scripts/kaggle_kernel_certifier.py certify \
  --profile /absolute/path/to/preflight-profile.json \
  --receipt /absolute/path/to/certification.json
```

Certification proceeds in this order:

1. Bind hashes and validate Kaggle metadata, source structure, offline mode, self-containment,
   mount inventories, sampling controls, environment requirements, and output contracts.
   The automatically triggered focused pre-push release debug materializes only the script/notebook
   that `kaggle kernels push` uploads. It rejects any kernel that needs a local sibling manifest,
   runtime module, checkpoint, wheel, or data file which has not instead been bound to a declared
   Kaggle input source. It also rejects undeclared third-party imports anywhere in the entrypoint
   and requires the dependency-probe marker in every scenario before release work can pass.
   It refuses a release asset when profile mounts do not map one-to-one onto metadata sources,
   when a Dataset mirror's `local_root` is not exactly the provider round-trip download root, or
   when any asserted root differs from the canonical root independently derived from metadata.
   The simulator stages at that derived root and never trusts the profile root to create its tree.
   When materialization rewrites overlapping roots independently, the adapter must prove an exact
   byte round-trip through the complete ordered transform. Reversing only the owner-qualified root,
   inferring the rewritten generic prefix from another field, or accepting a source hash after a
   partial inverse is a release blocker.
   Source-triggered runtime-safety gates additionally reject a `/proc` RSS monitor without a
   synthetic child-exits-between-polls proof, a release linker path without empty/trailing/relative
   inherited-value probes, a subprocess without bounded durable failure diagnostics, or MP4 release
   code without an exact promised-output/full-decode probe. Any dynamic `exec` additionally requires
   a registered-module target-minor probe; it must execute the exact embedded bytes with every
   module already present in `sys.modules` and prove dataclass loading under the declared provider
   interpreter.
   It also executes the exact outer-entrypoint late-tail probe under the declared target Python;
   every bound late-tail symbol must be top-level-defined and the probe must cross the heavy-stage
   handoff through final evidence creation. A profile that exercises only imports, re-entry, or an
   early-stop workload cannot be eligible.
   Before ladder timing is accepted, every ordinary run must produce the exact Step0
   deterministic-invariant receipt. The certifier independently validates every numeric
   namespace's full cardinality and canonical numeric order, and proves from stdout positions that
   the Step0 completion marker occurred exactly once before the heavy-work marker. Identity-
   expanded directory namespaces must bind every expanded root and all of its direct numeric
   directory names. A receipt written after heavy work is a release blocker.
   Static validation also rejects control-host executable/interpreter/command paths before the
   Step0 probe or any ladder run. A frozen profile that names a developer's Python binary is not
   target-runtime evidence.
2. Rebuild a fresh temporary `/kaggle/input`, `/kaggle/src`, and `/kaggle/working` for every run.
3. Deny Python networking and strip Kaggle credentials.
4. Execute every ladder role repeatedly with read-only inputs and a clean working directory.
5. Validate exit status, log markers, completion-unit receipt, file inventory, JSON/JSONL/CSV/ZIP
   structure, MP4 container structure plus hash-bound full decode through expected frame count and
   EOF, and byte-repeatability of at least one semantic output.
6. Project full runtime and peak RSS from repeated multi-scale observations and inflate for
   variance and measured local-to-remote ratios. Require projected memory below physical capacity;
   classify runtime against the LMT autonomous boundary without inventing a sub-cap.
7. Inject missing mount, missing required file, corrupted required file, and duplicate-basename
   faults when applicable. For numeric-indexed namespaces, also replay the full lexical-order
   boundary and inject a missing index, an out-of-range extra index, and a noncanonical alias
   spelling such as a leading-zero duplicate. Missing/corrupt/index faults must fail inside Step0
   before heavy work with neither a Step0 nor success receipt; expected-pass lexical and irrelevant
   duplicate cases must preserve the byte-repeatable semantic output.

On failure:

1. Use the receipt's stable failure class and evidence tail to identify one causal repair.
2. Add or retain a fixture that reproduces the exact signature.
3. Repair only the kernel or project adapter; never edit the certificate outcome.
4. Recompute all hashes.
5. Replay the complete certification, not only the failed case.

Stop and report a blocker when no observation-distinct causal repair remains, the adapter cannot
prove a workload control is honored, or the local environment cannot exercise the release path.

### 4. Adversarially review the eligible receipt

Before launch, inspect the receipt as a breaker:

- Can stale output satisfy the semantic receipt?
- Can a declared environment variable be ignored?
- Can recursive discovery select a wrong or duplicate carrier?
- Did Kaggle strip or insert a Dataset archive directory so the provider download root and the
  simulated remote mount differ in path depth?
- Can a self-consistent profile, kernel, and stale receipt all agree on a legacy short root that
  contradicts the owner-qualified Dataset/competition source in metadata?
- Can independently rewritten generic and owner-qualified competition roots overlap so that a
  one-step inverse restores one literal but leaves another embedded source string mutated?
- Can a sibling module or undeclared wheel be available only on the development machine?
- Can embedded dataclass-bearing source pass only because a test helper registered its module in
  `sys.modules`, while the released script executes it in a bare dictionary or on another Python
  minor version?
- Can dependency installation succeed but restart fail because an embedded module has a
  nonexistent synthetic `__file__`? Would restarting a materialized child skip wrapper completion
  or evidence sealing?
- Can every ladder role finish through a synthetic or early branch while the normal post-heavy
  outer tail still contains an unresolved name, missing helper, or unreachable completion writer?
- Can a tiny sample omit the slow or memory-heavy stratum?
- Can a numeric-indexed inventory pass on `0..9` yet fail on `0..10` because lexical order was
  compared with numeric order? Does the full-cardinality Step0 receipt prove canonical ordering,
  and do missing, extra, and alias index faults stop before the first heavy-work marker?
- Can a cheap deterministic raw-inventory, path, or cardinality gate still execute after
  `HEAVY_WORK_BEGIN`, even though the bounded computation itself succeeds?
- Can local warm-cache timing understate Kaggle cold-start and filesystem cost?
- Does any command, interpreter, or executable field still name `/Users/...`, a local `/home/...`,
  a Windows drive, or `~` rather than `{python}` or a target-resolved path?
- Can peak memory grow with workload size even when elapsed time looks safe?
- Can a child exit successfully between monitor polls, lose `/proc/<pid>/status` after reaping, and
  be mislabeled as a resource-monitor failure?
- Can an inherited `LD_LIBRARY_PATH` contain empty, trailing, doubled, relative, `$ORIGIN`, or
  mounted components? Is the child path reconstructed only from authenticated carrier and
  allowlisted host roots, or proven under target-like injected variants?
- If a platform child fails, are its return code, total byte counts, full-stream hashes, and bounded
  stdout/stderr tails persisted under `/kaggle/working` before temporary state is cleaned?
- Does every promised MP4 have a receipt bound to the actual video hash, exact decoded/expected
  frame count, decoder identity, and EOF—not merely a successful writer open or first-frame read?
- Can title normalization, kernel ID, source list, or expected version diverge at push time?
- Can a Dataset create reach Kaggle with a title outside 6..50 characters, a missing ID/privacy
  declaration, or metadata whose ID differs from the intended Dataset?
- Can the launcher consume a receipt for different bytes or consume it twice?
- Does the kernel still pass when its local folder is reduced to exactly the code file Kaggle sends?
  If not, stop: build and hash an explicit dataset/model/kernel-source carrier rather than assuming
  `kaggle kernels push` uploads package siblings.

Any credible yes is `REJECTED`, even if the script says eligible. Repair the gap and add a
machine check before launching.

### 5. Launch exactly once

At the launch boundary, re-hash the package and metadata and compare them to the eligible receipt.
Use the repository's approved authenticated launcher, shared serial lock, exact fresh-version
predicate, and quota ledger. Send once. Do not silently choose a new slug, overwrite an existing
version, bypass a lock, or reuse the receipt. If the user requested send-without-poll, stop after
the launcher confirms the push; submission is not a scientific success claim.

## Runtime authority

Treat runtime as an upper-envelope problem, not a mean-speed benchmark. The certifier uses
multi-scale pairwise slopes, repeat spread, fixed remote overhead, and a remote multiplier to
produce the authenticated projection. Those are estimation controls, not autonomy limits.

- With no matched timing pairs, use `remote_multiplier >= 1.5`.
- With 1–4 matched pairs, cover `1.15 × max(remote/local)`.
- With at least 5 matched pairs, cover `1.10 × empirical p95(remote/local)`.

Apply the autonomous projection cap only from `LMT.md`, with no agent-imposed wall-clock kill. At
or above that cap, emit `APPROVAL_REQUIRED`; do not reject the
science, shard around the boundary, or launch autonomously. Never add fractional runtime or memory
eligibility caps in a profile.

## Resource routing

Resolve every relative resource path below against the directory containing this `SKILL.md`.

- Run `scripts/kaggle_kernel_certifier.py` for profile generation, simulation, certification,
  machine-readable receipts, and self-tests.
- Read [profile-contract.md](references/profile-contract.md) while creating an adapter.
- Read [failure-taxonomy.md](references/failure-taxonomy.md) after any kernel error or when adding
  an adversarial regression.
- Read [reexec-lifecycle.md](references/reexec-lifecycle.md) whenever release code hashes, opens,
  or re-executes `Path(__file__).resolve()`.
- Copy `assets/preflight-profile.template.json` only when `init-profile` cannot inspect the package.

## Skill integrity check

After changing this skill, run:

```bash
python3 scripts/kaggle_kernel_certifier.py self-test
python3 /path/to/skill-creator/scripts/quick_validate.py /path/to/ship-kaggle-kernels
```

The self-test must show one eligible fixture, reject dependency/output/broad-discovery/ignored-
control/corrupt-input fixtures and a false legacy short provider root, and return
`APPROVAL_REQUIRED` at the LMT runtime boundary. It must also exercise an end-to-end eligible
dual-root materialization fixture and reject a wrong inverse order and every partial inverse that
does not restore all bound source hashes. It must also exercise an end-to-end eligible
runtime-safety probe set, synthetically place a successful child exit between RSS polls, reject
unregistered target-minor dynamic modules and unproved monitor/linker/media release paths, validate
durable bounded child diagnostics, and reject an MP4 receipt whose decoded frame count does not
reach the promised count/EOF.
It must also reject a missing dependency re-exec lifecycle, a synthetic dynamic-module reexec file,
and a child-only restart that bypasses the outer wrapper. It must reject a missing exact post-heavy
outer-tail probe and any bound late-tail helper absent from the transmitted module's top level.
It must exercise both an exact direct-file numeric namespace and a 21-identity x 100-name direct-
directory namespace whose lexical and numeric orders differ, bind every expanded root in the
numeric Step0 receipt, reject lexical receipt order and a Step0 completion marker after heavy work,
and prove directory missing/extra/alias index faults fail before heavy work without receipts.
It must reject a macOS control-host Python path during static validation with no Step0 probe,
simulation, runtime-safety probe, adversarial run, or heavy-work marker reached.
When the repository supplies `scripts/cmux_ops.py`, also run its unit suite and require explicit
coverage showing that 6- and 50-character Dataset titles reach only the fake subprocess while a
51-character title, missing/mismatched ID, or non-boolean privacy declaration invokes no process.

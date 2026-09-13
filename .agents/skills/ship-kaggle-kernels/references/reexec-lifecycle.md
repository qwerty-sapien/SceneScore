# Saved-script dependency re-exec lifecycle

Use this contract whenever the release entrypoint or an embedded source hashes, opens, or
re-executes `Path(__file__).resolve()`.

The dynamic module's `__file__` must resolve to Kaggle's real outer saved-script entrypoint. It
must be a regular non-symlink file whose bytes are the frozen package artifact. The dependency
marker/token binds those bytes. The re-exec argv must target the same outer entrypoint, so the
second interpreter executes wrapper Step 0, dynamic-module registration, completion handling,
diagnostics, and evidence sealing.

The target-minor probe must demonstrate:

- the initial and dynamic-module files are the same regular outer entrypoint;
- a fresh interpreter re-entered that wrapper;
- the dependency marker/token authenticated against the same bytes;
- completion and evidence-writing code remained reachable; and
- a second restart was refused.

Reject a synthetic uncreated `module.__file__`, and reject materializing/re-executing an embedded
child whenever the wrapper owns completion or sealing. Import/dataclass identity alone does not
exercise this lifecycle.

```json
{
  "runtime_safety": {
    "dynamic_module_execution": {
      "mode": "registered_target_minor_probe",
      "reexec_lifecycle": {
        "mode": "outer_saved_script_reentry_probe",
        "reexec_module_name": "embedded_exporter_module",
        "entrypoint_marker": "WRAPPER_REEXEC_LIFECYCLE_PASS",
        "receipt_path": "REEXEC_LIFECYCLE.json",
        "probe": {}
      }
    }
  }
}
```

The probe object follows the normal runtime-safety probe schema and uses the exact target Python
executable.

"""python -m modules.muse.acquisition --help"""
import argparse
import json
from pathlib import Path
import sys
from modules.muse.acquisition.store import (Recorder, read_json, replay, recover, export_session, delete_session,
                                           manifest, encoded, MAX_CHUNK_BYTES)
from modules.muse.acquisition.live import health, capture_lsl
from modules.muse.acquisition.diagnostics import diagnose_transport
from modules.muse.acquisition.protocol import collect_session, review_session
from modules.muse.baseline.causal import CausalBaseline, Config
from modules.muse.annotation.workflow import cues, confirm, label


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local Muse tools; replay/synthetic are visibly labelled, no training")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("health")
    diag = commands.add_parser("diagnose", help="Bounded advertised LSL metadata only; no recording")
    diag.add_argument("--source-id")
    diag.add_argument("--timeout-s", type=float, default=2.0)
    collect = commands.add_parser("collect", help="Consented foreground collection; delayed independent labelling follows")
    collect.add_argument("session", type=Path)
    collect.add_argument("metadata", type=Path)
    collect.add_argument("--protocol", type=Path, required=True)
    collect.add_argument("--source-id", required=True)
    collect.add_argument("--seconds", type=float, required=True)
    collect.add_argument("--start", action="store_true", required=True)
    review = commands.add_parser("review", help="Read-only raw count/exposure review")
    review.add_argument("session", type=Path)
    record = commands.add_parser("record-file", help="Commit canonical input chunks unchanged; not live capture")
    record.add_argument("session", type=Path)
    record.add_argument("metadata", type=Path)
    record.add_argument("input", type=Path)
    record.add_argument("--start", action="store_true", required=True)
    record.add_argument("--max-chunks", type=int, default=10000)
    live = commands.add_parser("capture-lsl", help="Optional existing verified LSL stream; explicit visible start")
    live.add_argument("session", type=Path)
    live.add_argument("metadata", type=Path)
    live.add_argument("--source-id", required=True)
    live.add_argument("--seconds", type=float, required=True)
    live.add_argument("--consent", action="store_true", required=True)
    rep = commands.add_parser("replay", help="Exact canonical records to stdout, no realtime scheduling")
    rep.add_argument("session", type=Path)
    rep.add_argument("--detect", action="store_true")
    rep.add_argument("--arm-after-s", type=float, help="Explicit replay arming after warmup; never auto-rearm after a fault")
    rep.add_argument("--config", type=Path)
    for name in ("recover", "inspect"):
        sub = commands.add_parser(name)
        sub.add_argument("session", type=Path)
    exp = commands.add_parser("export")
    exp.add_argument("session", type=Path)
    exp.add_argument("destination", type=Path)
    delete = commands.add_parser("delete")
    delete.add_argument("session", type=Path)
    delete.add_argument("--confirm-session-id", required=True)
    cue = commands.add_parser("cues", help="Generate local intent schedule; not actual blink truth")
    cue.add_argument("session", type=Path)
    cue.add_argument("--mode", required=True)
    cue.add_argument("--seed", type=int, default=0)
    cue.add_argument("--count", type=int, default=10)
    response = commands.add_parser("confirm")
    response.add_argument("session", type=Path)
    response.add_argument("cue_id")
    response.add_argument("--performed", required=True)
    response.add_argument("--confirmation-s", type=float, required=True)
    lab = commands.add_parser("label", help="Independent post-session review/relabel, never detector truth")
    lab.add_argument("session", type=Path)
    for name in ("reviewer", "source", "evidence-ref", "epoch", "intent", "certainty"):
        lab.add_argument("--" + name, required=True)
    for name in ("onset-s", "end-s", "final-blink-s"):
        lab.add_argument("--" + name, type=float, required=True)
    lab.add_argument("--gesture-count", type=int, required=True)
    lab.add_argument("--supersedes")
    args = parser.parse_args(argv)
    try:
        result = None
        if args.command == "health":
            result = health()
        elif args.command == "diagnose":
            result = diagnose_transport(source_id=args.source_id, timeout_s=args.timeout_s)
        elif args.command == "collect":
            result = collect_session(args.session, read_json(args.metadata), protocol=read_json(args.protocol),
                                     source_id=args.source_id, seconds=args.seconds, explicitly_started=args.start,
                                     report=lambda value: print(json.dumps(value, allow_nan=False), file=sys.stderr))
        elif args.command == "review":
            result = review_session(args.session)
        elif args.command == "record-file":
            if not 1 <= args.max_chunks <= 100000:
                raise ValueError("chunk_budget_out_of_range")
            recorder = Recorder(args.session, read_json(args.metadata), explicitly_started=args.start)
            print("RECORDING local file import, mode=" + recorder.metadata["provenance"]["source_mode"], file=sys.stderr)
            reason = "complete"
            try:
                with args.input.open("rb") as source:
                    for number in range(args.max_chunks + 1):
                        line = source.readline(MAX_CHUNK_BYTES + 1)
                        if not line:
                            break
                        if number == args.max_chunks or len(line) > MAX_CHUNK_BYTES:
                            raise ValueError("input_budget_exceeded")
                        recorder.append(json.loads(line))
            except BaseException:
                reason = "interrupted_or_invalid_input"
                raise
            finally:
                recorder.close(reason)
            result = {"status": reason, "recording": False}
        elif args.command == "capture-lsl":
            result = capture_lsl(args.session, read_json(args.metadata), source_id=args.source_id,
                                 seconds=args.seconds, consent=args.consent)
        elif args.command == "replay":
            meta = manifest(args.session)["metadata"]
            print("REPLAY original_mode=" + meta["provenance"]["source_mode"] + "; no headset or realtime claim", file=sys.stderr)
            baseline = CausalBaseline(meta, Config(**read_json(args.config)) if args.config else Config()) if args.detect else None
            armed_once, start = False, None
            for chunk in replay(args.session):
                if not baseline:
                    sys.stdout.buffer.write(encoded(chunk))
                    continue
                start = chunk["device_times_s"][0] if start is None else start
                candidates, gestures = baseline.consume(chunk)
                if (args.arm_after_s is not None and not armed_once
                        and chunk["device_times_s"][-1] - start >= args.arm_after_s):
                    baseline.arm()
                    armed_once = True
                for event in candidates + gestures:
                    sys.stdout.buffer.write(encoded(event))
                print(json.dumps({"mode": "replay", "armed": baseline.armed, "reason": baseline.reason,
                                  "overlong_rejection": baseline.grammar.last_rejection,
                                  "raw_frontal": {meta["channels"][i]["name"]: chunk["samples"][-1][i]
                                                  for i in baseline.indices}}), file=sys.stderr)
            # EOF never invents elapsed device time to complete a gesture.
        elif args.command == "inspect":
            result = manifest(args.session)
        elif args.command == "recover":
            result = recover(args.session)
        elif args.command == "export":
            result = export_session(args.session, args.destination)
        elif args.command == "delete":
            delete_session(args.session, confirmed_session_id=args.confirm_session_id)
            result = {"deleted": args.confirm_session_id}
        elif args.command == "cues":
            result = cues(args.session, mode=args.mode, seed=args.seed, count=args.count)
        elif args.command == "confirm":
            result = confirm(args.session, args.cue_id, performed=args.performed, confirmation_s=args.confirmation_s)
        elif args.command == "label":
            values = vars(args).copy()
            values.pop("command")
            path = values.pop("session")
            result = label(path, **values)
        if result is not None:
            print(json.dumps(result, sort_keys=True, allow_nan=False))
        if args.command == "diagnose" and result["status"] == "BLOCKED":
            return 2
        return 0
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as exc:
        print(json.dumps({"code": "MUSE_OPERATION_FAILED", "message": str(exc), "retryable": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

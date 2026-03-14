#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def read_last_jsonl(path: Path):
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except Exception:
        return None


def count_status(path: Path, since_ts: int):
    ok = 0
    err = 0
    trade_actions = 0
    if not path.exists():
        return ok, err, trade_actions
    for ln in path.read_text(encoding="utf-8").splitlines():
        try:
            o = json.loads(ln)
        except Exception:
            continue
        ts = int(o.get("ts", 0) or 0)
        if ts < since_ts:
            continue
        status = o.get("status")
        if status == "ok":
            ok += 1
        elif status == "error":
            err += 1
        action = ((o.get("plan") or {}).get("action") or "").lower()
        if action in {"open", "scale", "flip", "close"}:
            trade_actions += 1
    return ok, err, trade_actions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/var/lib/avantis-paper-bot/data")
    ap.add_argument("--hours", type=int, default=4)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    since_ts = int(now.timestamp()) - args.hours * 3600
    day = now.date().isoformat()

    data = Path(args.data_dir)
    strategies_root = data / "strategies"
    strategy_ids = sorted([p.name for p in strategies_root.iterdir() if p.is_dir()]) if strategies_root.exists() else []

    print(f"APB health report @ {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"window: last {args.hours}h")
    print("")

    if not strategy_ids:
        print("No strategy directories found.")
        return

    for sid in strategy_ids:
        journal = strategies_root / sid / "journal" / f"{day}.jsonl"
        snap = strategies_root / sid / "state" / "snapshot.json"
        ok, err, trades = count_status(journal, since_ts)
        last = read_last_jsonl(journal)
        snap_ts = None
        if snap.exists():
            try:
                snap_o = json.loads(snap.read_text(encoding="utf-8"))
                snap_ts = int(snap_o.get("ts", 0) or 0)
            except Exception:
                pass

        print(f"- {sid}")
        print(f"  - cycles: ok={ok} error={err} trades={trades}")
        print(f"  - journal: {'present' if journal.exists() else 'missing'}")
        if last:
            print(f"  - last cycle ts: {last.get('ts')} status={last.get('status')} action={((last.get('plan') or {}).get('action'))}")
        if snap_ts:
            print(f"  - snapshot ts: {snap_ts}")


if __name__ == "__main__":
    main()

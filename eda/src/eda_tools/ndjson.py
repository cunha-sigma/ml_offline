"""Loaders for the batch_03 ndjson data samples.

Three firehose files (joined bid request + impression + optional video
activity, one JSON event per line) and one delivery-control export
(entity records: organization / ad_account / campaign / adset / ad).
Default paths point at `docs/batch_03/data-samples/` in this repo;
every loader accepts explicit paths instead.
"""

import json
from collections.abc import Iterator, Sequence
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "docs" / "batch_03" / "data-samples"
TRAFFIC_DIR = REPO_ROOT / "docs" / "batch_03" / "md" / "traffic_and_workload_metrics"
FIREHOSE_FILES = tuple(sorted(DATA_DIR.glob("firehose-full-*.ndjson")))
DELIVERY_CONTROL_FILE = DATA_DIR / "sigma_sample_file.ndjson"

PathLike = str | Path


def iter_ndjson(path: PathLike) -> Iterator[dict]:
    """Yield one parsed JSON object per non-empty line."""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def read_ndjson(path: PathLike, normalize: bool = True) -> pd.DataFrame:
    """Read any ndjson file into a DataFrame.

    With normalize=True nested dicts become dot-joined columns
    (lists are kept as object columns).
    """
    records = list(iter_ndjson(path))
    if normalize:
        return pd.json_normalize(records)
    return pd.DataFrame(records)


def _auction_key(auctionid: dict | None) -> str | None:
    """Scalar join key from the auctionid struct {hostid, tid, timestamp}."""
    if not auctionid:
        return None
    return f"{auctionid.get('timestamp')}.{auctionid.get('tid')}.{auctionid.get('hostid')}"


def _firehose_paths(paths: Sequence[PathLike] | None) -> list[Path]:
    resolved = [Path(p) for p in paths] if paths is not None else list(FIREHOSE_FILES)
    if not resolved:
        raise FileNotFoundError(f"no firehose files found under {DATA_DIR}")
    return resolved


def load_firehose(paths: Sequence[PathLike] | None = None) -> pd.DataFrame:
    """One row per joined firehose event.

    Flattens `impression.*` and `request.*` (including
    `request.bidrequest.*`) into dot-joined columns and adds
    `source_file`, `candidate_count`, and `activity_count`. The raw
    `request.adcandidates` and `activity` lists are dropped — use
    load_candidates() / load_activity() for those.
    """
    rows = []
    for path in _firehose_paths(paths):
        for rec in iter_ndjson(path):
            rec = dict(rec)
            request = dict(rec.get("request") or {})
            candidates = request.pop("adcandidates", None) or []
            activity = rec.pop("activity", None) or []
            rec["request"] = request
            rec["auction_key"] = _auction_key(
                request.get("auctionid") or (rec.get("impression") or {}).get("auctionid")
            )
            rec["source_file"] = Path(path).name
            rec["candidate_count"] = len(candidates)
            rec["activity_count"] = len(activity)
            rows.append(rec)
    return pd.json_normalize(rows)


def load_candidates(paths: Sequence[PathLike] | None = None) -> pd.DataFrame:
    """One row per ad candidate, with join keys and request context.

    Candidate fields are flattened (`bidding.*`, `pacing.*`); each row
    carries `auction_key` and `source_file` to join back to the event,
    plus app/device/bidfloor context from the bid request.
    """
    rows = []
    for path in _firehose_paths(paths):
        for rec in iter_ndjson(path):
            request = rec.get("request") or {}
            bidrequest = request.get("bidrequest") or {}
            app = bidrequest.get("app") or {}
            device = bidrequest.get("device") or {}
            geo = device.get("geo") or {}
            imps = bidrequest.get("imp") or []
            context = {
                "auction_key": _auction_key(request.get("auctionid")),
                "source_file": Path(path).name,
                "inventory_source": request.get("inventory_source"),
                "app.bundle": app.get("bundle"),
                "app.name": app.get("name"),
                "device.devicetype": device.get("devicetype"),
                "device.os": device.get("os"),
                "geo.country": geo.get("country"),
                "imp0.bidfloor": imps[0].get("bidfloor") if imps else None,
            }
            for cand in request.get("adcandidates") or []:
                rows.append({**context, **cand})
    return pd.json_normalize(rows)


def load_activity(paths: Sequence[PathLike] | None = None) -> pd.DataFrame:
    """One row per video activity event (START, Q1, MID, Q3, ...)."""
    rows = []
    for path in _firehose_paths(paths):
        for rec in iter_ndjson(path):
            for event in rec.get("activity") or []:
                rows.append(
                    {
                        **event,
                        "auction_key": _auction_key(event.get("auctionid")),
                        "source_file": Path(path).name,
                    }
                )
    return pd.json_normalize(rows)


def load_delivery_control(path: PathLike | None = None) -> pd.DataFrame:
    """The delivery-control export: one row per entity record.

    Split by the `entity_type` column (organization / ad_account /
    campaign / adset / ad); `ua_*_id` fields link child to parent.
    """
    return read_ndjson(path if path is not None else DELIVERY_CONTROL_FILE)

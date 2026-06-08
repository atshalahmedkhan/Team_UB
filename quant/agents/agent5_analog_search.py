"""Agent 5 — Elastic kNN analog search + MongoDB enrichment.

This lightweight agent uses the `elastic_index` MongoDB fallback to find
nearest historical market state dates and returns a small summary with
similarity and observed forward-return statistics (if present).
"""

from __future__ import annotations

from typing import Any, Dict, List
import statistics

from quant.storage.elastic_index import knn_query
from quant.storage.mongo_client import db


def _collect_outcomes(docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    vals_30 = []
    vals_60 = []
    vals_90 = []
    for d in docs:
        date = d.get("date")
        doc = db["market_states"].find_one({"date": date}) if db is not None else None
        if not doc:
            continue
        ret = doc.get("ret_30d") or doc.get("ret_30") or None
        if ret is not None:
            vals_30.append(float(ret))
        ret = doc.get("ret_60d") or doc.get("ret_60") or None
        if ret is not None:
            vals_60.append(float(ret))
        ret = doc.get("ret_90d") or doc.get("ret_90") or None
        if ret is not None:
            vals_90.append(float(ret))

    def stats(vs: List[float]):
        if not vs:
            return {"n": 0, "median": None}
        return {"n": len(vs), "median": statistics.median(vs)}

    return {"ret_30d": stats(vals_30), "ret_60d": stats(vals_60), "ret_90d": stats(vals_90)}


def run(fingerprint: Dict[str, Any], k: int = 10) -> Dict[str, Any]:
    vector = fingerprint.get("vector")
    if not vector:
        raise ValueError("Fingerprint must include a `vector` key")

    neighbors = knn_query(vector, k=k)
    outcomes = _collect_outcomes(neighbors)

    return {"analogs": neighbors, "outcomes": outcomes}


def main() -> None:
    import argparse
    from pathlib import Path
    import json

    parser = argparse.ArgumentParser(description="Run analog search for a given fingerprint JSON file")
    parser.add_argument("--fingerprint", help="Path to fingerprint JSON file", required=False)
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()

    if args.fingerprint:
        fp = json.loads(Path(args.fingerprint).read_text())
    else:
        # Attempt to load today's fingerprint from MongoDB
        if db is None:
            raise RuntimeError("MongoDB not configured and no fingerprint provided")
        today = db["market_states"].find_one({"date": "today"})
        if not today:
            raise RuntimeError("No today's fingerprint found in MongoDB; run fingerprint agent first")
        fp = {"vector": today.get("market_vector")}

    result = run(fp, k=args.k)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

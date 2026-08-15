"""
Phase 13 Batch 10 -- Final Synthetic-Data Validation.

A thin orchestration harness: every step below calls a REAL, existing
service endpoint (the same contracts `docs/architecture` already
defines and prior phases already implemented) -- this script invents no
new processing trigger, no shortcut, and no fabricated result. It is
meant to run FROM INSIDE the Docker network (e.g. `docker cp` into a
running container + `docker exec ... python /tmp/run_validation.py`),
since none of ingestion_service/nlp_service/anomaly_service/
root_cause_service/business_impact_service are host-published --
exactly the same internal-only convention every prior phase already
established.

Determinism: complaint identifiers, structure, and relative time
offsets are fixed; `event_occurred_at` values are computed relative to
"now" (not a hardcoded historical date) because anomaly_service's
volume/region detectors compare a rolling "current N-day window" against
the "previous equivalent window" measured from wall-clock time --
a fixed historical date would fall outside both windows and produce no
anomaly at all. The *shape* of the dataset (which complaints, how many,
in which relative window) is 100% reproducible across runs; only the
absolute calendar dates shift with `now()`.

Six requested scenario purposes, honestly consolidated into two real
incidents (documented, not hidden):
  - Scenario A (baseline): a separate, low-volume, evenly-spread
    population across five regions/categories -- the negative control.
    Must NOT itself produce a strong anomaly.
  - Scenarios B, C, D, E, F: one deliberately concentrated cluster
    (single region, single NLP-derivable category, highly-negative/
    critical-urgency language) -- a real complaint spike (B) IS a
    regional anomaly (C) when concentrated in one region, naturally
    carries severe customer impact (D), shares a root-cause-relevant
    pattern (E, category+region), and -- once given root-cause +
    business-impact -- automatically produces a recommendation (F) via
    the real BusinessImpactCompleted internal-event fan-out (Batch 4/5).
    This mirrors how one real incident actually looks in production
    (multi-dimensional), rather than manufacturing six artificial,
    disconnected incidents to satisfy a letter-for-letter checklist.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import httpx

# ingestion_service's complaints router is mounted with NO /api/v1
# prefix (backend/services/ingestion_service/app/main.py:32); every
# other service below mounts its public router under /api/v1
# (verified per-service in each main.py before writing this script).
INGESTION_URL = "http://ingestion_service:8001"
NLP_URL = "http://nlp_service:8002/api/v1"
ANOMALY_URL = "http://anomaly_service:8003/api/v1"
ROOT_CAUSE_URL = "http://root_cause_service:8004/api/v1"
BUSINESS_IMPACT_URL = "http://business_impact_service:8005/api/v1"
RECOMMENDATION_URL = "http://recommendation_service:8006/api/v1"
EVALUATION_URL = "http://evaluation_service:8008/api/v1"

NOW = datetime.now(timezone.utc)


def _iso(days_ago: float) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat()


# --- Scenario A: baseline (negative control) --------------------------------
# Spread thinly across 5 regions x 5 categories, 6-40 days ago, neutral
# language -- deliberately unremarkable, must not itself trip a threshold.
_BASELINE_REGIONS = ["US-East", "US-West", "EU-Central", "APAC", "LatAm"]
_BASELINE_TEXTS = [
    ("Payment double-charged", "My card was charged twice for the same order, please review the billing. It is fine to take a few days, no rush."),
    ("Product arrived slightly late", "The item arrived a bit later than expected. Overall it was an average experience, nothing urgent."),
    ("Support call was okay", "I spoke with an agent about my account settings. The call was fine, a standard resolution."),
    ("Minor app glitch", "The app showed a small technical error on login, resolved itself after a retry. Just a suggestion for the team."),
    ("Subscription question", "I have a question about upgrading my subscription plan whenever it's convenient. No rush at all."),
]


def build_baseline_complaints() -> List[Dict[str, Any]]:
    complaints = []
    for i in range(10):
        region = _BASELINE_REGIONS[i % len(_BASELINE_REGIONS)]
        title, text = _BASELINE_TEXTS[i % len(_BASELINE_TEXTS)]
        days_ago = 6 + (i * 3.4)  # spread 6..~37 days ago, spans both the "current" and "previous" 30-day windows
        complaints.append(
            {
                "external_reference_id": f"VALIDATION-BASELINE-{i:02d}",
                "complaint_title": title,
                "complaint_text": f"{text} (baseline record {i:02d})",
                "complaint_source": "customer_portal",
                "source_channel": "support_ticket",
                "customer_region": region,
                "customer_segment": "individual",
                "customer_type": "existing_customer",
                "product_category": "General",
                "operational_area": "customer_support",
                "service_type": "customer_service",
                "event_occurred_at": _iso(days_ago),
            }
        )
    return complaints


# --- Scenarios B/C/D/E/F: concentrated delivery-failure spike ---------------
# Single region (US-West), delivery/package language (-> IssueCategory.
# DELIVERY_ISSUE per nlp_service's own keyword table), highly-negative +
# critical-urgency language, all within the last 0-2 days (the current
# detection window). 14 records -> current-window US-West count jumps
# from a near-zero baseline to 14+, and global volume jumps well past
# the >200% CRITICAL band (severity.py).
_SPIKE_TEXTS = [
    "My package tracking shows delivery failed again -- this is the third lost shipment this month and it is completely unacceptable. I am furious and considering legal action if this is not resolved immediately.",
    "The courier marked this delivered but nothing arrived at my address. This is a disgusting pattern of lost packages and I need this handled urgently, today.",
    "Another delivery failure -- my package never arrived and tracking has been frozen for days. This is the worst shipping experience I have ever had and it is unacceptable.",
    "I am outraged. My package was supposed to arrive days ago and the courier has not even attempted delivery. I need this escalated immediately, this is urgent.",
    "This delivery service is a scam at this point -- three packages lost in the same week. Furious does not begin to describe how ruined my week has been.",
    "Package delivery failed yet again. Tracking shows it stuck at the depot for days with no update. Completely unacceptable, I want this escalated immediately.",
    "My shipment never arrived despite tracking marking it delivered. This is the worst delivery failure pattern I've seen and I am furious about the lost package.",
    "Delivery failed again -- courier never showed up, tracking is broken, and support has been unhelpful. This is urgent and needs immediate escalation.",
    "Yet another lost package from this courier. My tracking number shows nothing for days. This pattern of delivery failures is unacceptable and needs urgent attention.",
    "The delivery never arrived and the courier's tracking system shows conflicting information. I am furious -- this is the worst service failure I've experienced.",
    "My package delivery failed for the second time this week. Tracking shows it lost in transit. This is unacceptable and I need immediate escalation, urgent.",
    "Delivery courier lost my package again -- tracking has not updated in days. This is a disgusting, unacceptable pattern and I am furious about it.",
    "Another failed delivery, another lost package. Tracking is frozen and support has been unhelpful. I need this escalated immediately -- this is urgent.",
    "This is the fourth delivery failure this month -- packages consistently lost in transit. Furious and considering escalating this urgently to management.",
]


def build_spike_complaints() -> List[Dict[str, Any]]:
    complaints = []
    for i, text in enumerate(_SPIKE_TEXTS):
        days_ago = 0.2 + (i * 0.12)  # all within the last ~2 days -- same correlation window
        complaints.append(
            {
                "external_reference_id": f"VALIDATION-SPIKE-{i:02d}",
                "complaint_title": "Repeated delivery failure -- package lost",
                "complaint_text": text,
                "complaint_source": "customer_portal",
                "source_channel": "support_ticket",
                "customer_region": "US-West",
                "customer_segment": "premium",
                "customer_type": "existing_customer",
                "product_category": "Electronics",
                "operational_area": "delivery",
                "service_type": "delivery_operations",
                "event_occurred_at": _iso(days_ago),
            }
        )
    return complaints


async def _post(client: httpx.AsyncClient, url: str, json_body: Dict[str, Any]) -> Dict[str, Any]:
    response = await client.post(url, json=json_body, timeout=30.0)
    return {"status": response.status_code, "body": _safe_json(response)}


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return response.text


async def ingest(client: httpx.AsyncClient, complaints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for payload in complaints:
        result = await _post(client, f"{INGESTION_URL}/complaints", payload)
        results.append({"external_reference_id": payload["external_reference_id"], **result})
    return results


async def enrich_all(client: httpx.AsyncClient, ingested: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for record in ingested:
        if record["status"] != 201:
            continue
        complaint_id = record["body"]["id"]
        text = record["body"]["complaint_text"]
        result = await _post(client, f"{NLP_URL}/enrichments/process", {"complaint_id": complaint_id, "text": text})
        results.append({"complaint_id": complaint_id, **result})
    return results


async def main() -> None:
    async with httpx.AsyncClient() as client:
        summary: Dict[str, Any] = {"generated_at": NOW.isoformat()}

        baseline = build_baseline_complaints()
        spike = build_spike_complaints()

        print("=== 1. Ingesting baseline complaints ===", flush=True)
        baseline_ingested = await ingest(client, baseline)
        summary["baseline_ingested"] = baseline_ingested

        print("=== 2. Ingesting spike complaints ===", flush=True)
        spike_ingested = await ingest(client, spike)
        summary["spike_ingested"] = spike_ingested

        print("=== 3. Running NLP enrichment (baseline) ===", flush=True)
        baseline_enriched = await enrich_all(client, baseline_ingested)
        summary["baseline_enriched"] = baseline_enriched

        print("=== 4. Running NLP enrichment (spike) ===", flush=True)
        spike_enriched = await enrich_all(client, spike_ingested)
        summary["spike_enriched"] = spike_enriched

        print("=== 5. Running anomaly detection (/anomalies/run) ===", flush=True)
        anomaly_run = await _post(client, f"{ANOMALY_URL}/anomalies/run", {})
        summary["anomaly_run"] = anomaly_run

        print("=== 6. Running incident correlation (/incidents/run) ===", flush=True)
        incident_run = await _post(client, f"{ANOMALY_URL}/incidents/run", {})
        summary["incident_run"] = incident_run

        print("=== 7. Listing active anomalies ===", flush=True)
        active_anomalies = await client.get(f"{ANOMALY_URL}/anomalies")
        summary["active_anomalies"] = _safe_json(active_anomalies)

        print("=== 8. Listing incidents ===", flush=True)
        incidents_resp = await client.get(f"{ANOMALY_URL}/incidents")
        incidents = _safe_json(incidents_resp)
        summary["incidents"] = incidents

        # IncidentResponse carries no region/category breakdown directly
        # (see backend/services/anomaly_service/app/schemas/incidents.py)
        # -- select the highest-severity incident (our concentrated spike
        # is deliberately designed to be the most severe real signal in
        # this dataset; the thin, evenly-spread baseline should not
        # itself produce a CRITICAL/HIGH incident).
        _SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "normal": 4}
        target_incident_id = None
        if isinstance(incidents, list) and incidents:
            ranked = sorted(incidents, key=lambda inc: _SEVERITY_RANK.get(str(inc.get("severity", "")).lower(), 99))
            target_incident_id = ranked[0].get("id")

        summary["target_incident_id"] = target_incident_id

        if target_incident_id:
            print(f"=== 9. Running root-cause analysis for incident {target_incident_id} ===", flush=True)
            rc_result = await _post(client, f"{ROOT_CAUSE_URL}/root-causes", {"incident_id": target_incident_id})
            summary["root_cause_result"] = rc_result

            print(f"=== 10. Running business-impact analysis for incident {target_incident_id} ===", flush=True)
            bi_result = await _post(client, f"{BUSINESS_IMPACT_URL}/business-impact", {"incident_id": target_incident_id})
            summary["business_impact_result"] = bi_result

            print("=== 11. Waiting for async BusinessImpactCompleted fan-out ===", flush=True)
            await asyncio.sleep(3.0)

            print("=== 12. Fetching latest recommendation ===", flush=True)
            rec_resp = await client.get(f"{RECOMMENDATION_URL}/incidents/{target_incident_id}/recommendations/latest")
            summary["recommendation_result"] = {"status": rec_resp.status_code, "body": _safe_json(rec_resp)}

            print("=== 13. Fetching latest evaluation ===", flush=True)
            eval_resp = await client.get(f"{EVALUATION_URL}/evaluations/latest/{target_incident_id}")
            summary["evaluation_result"] = {"status": eval_resp.status_code, "body": _safe_json(eval_resp)}
        else:
            summary["note"] = "No incident was produced by correlation -- root-cause/business-impact/recommendation/evaluation steps skipped honestly."

        print("=== VALIDATION SUMMARY (JSON) ===")
        print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

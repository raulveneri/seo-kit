"""Versioned checklist accounting. These weights are kit policy, not ranking factors."""

from collections import defaultdict
from copy import deepcopy

SCORING_VERSION = 2

# Stable IDs also form the external evidence contract. Missing items stay unknown.
CONTENT_COMMON = {
    "intent": "The page fulfils its declared reader task and observed search intent.",
    "original_value": "The page adds useful original information or analysis.",
    "accuracy": "Consequential claims, references and changing details were checked.",
    "responsibility": "Authorship and appropriate expertise or responsibility are clear.",
    "completion": "Readers can complete the task without essential information gaps.",
    "presentation": "The main content is readable, identifiable and usable on mobile.",
    "discovery": "Relevant crawlable internal links connect this page to the site.",
    "metadata": "Title, main heading, description and visible content agree.",
}
CONTENT_TYPES = {
    "generic": {},
    "blog": {"dates": "Publication and substantive update dates are honest and consistent."},
    "guide": {
        "instructions": "Steps, prerequisites and examples fit the reader's task.",
        "limitations": "Relevant exceptions, risks and limits are explained.",
    },
    "review": {
        "experience": "Claims of testing or experience have inspectable evidence.",
        "comparison": "Decision criteria, alternatives, benefits and drawbacks are explained.",
    },
    "landing": {"offer": "The actual offer, scope, evidence and next action are clear."},
    "product": {"offer": "Product identity, variant, price and availability match the actual offer."},
}
REVIEW_ITEMS = {
    "geo.review": {
        "access": "Crawling, snippet eligibility and effective generative inclusion were reviewed.",
        "claims": "Page claims and structured data match visible, supported information.",
        "identity": "Business or author identity and substantive update dates are accurate.",
        "measurement": "Available impression or sampled-answer evidence has explicit scope and limits.",
    },
    "offpage.review": {
        "link_evidence": "Dated link evidence has explicit sample and provider limitations.",
        "link_quality": "Source-page relevance and suspected manipulation were reviewed.",
        "identity": "Applicable business identity and review practices were checked.",
    },
}
STATUSES = {"pass", "fail", "unmeasured", "not_applicable"}


def reviewed_items(key, item, page_locations):
    """Expand reviewed evidence. A legacy blanket verdict earns no qualitative credit."""
    if key == "onpage.intent_review":
        pages = item.get("pages", {})
        if not isinstance(pages, dict) or set(pages) - set(page_locations):
            raise ValueError(f"{key}: pages must use audited absolute page URLs")
        groups = []
        for url, location in page_locations.items():
            page = pages.get(url, {})
            if not isinstance(page, dict):
                raise ValueError(f"{key}: each page must be an object")
            kind = page.get("page_type", "generic")
            if not isinstance(kind, str) or kind not in CONTENT_TYPES:
                raise ValueError(f"{key}: unsupported page_type")
            groups.append((location, CONTENT_COMMON | CONTENT_TYPES[kind], page.get("items", {})))
    else:
        groups = [(item["scope"], REVIEW_ITEMS[key], item.get("items", {}))]
    findings = []
    for location, expected, supplied in groups:
        if not isinstance(supplied, dict) or set(supplied) - set(expected):
            raise ValueError(f"{key}: unknown review item IDs")
        for identifier, criterion in expected.items():
            value = supplied.get(identifier)
            if value is None:
                status, detail = "unmeasured", "No item-level review supplied. " + criterion
                if isinstance(item.get("status"), str) and item["status"] in {"pass", "fail"}:
                    detail += f" Legacy unscored verdict: {item['status']}, {item.get('detail', '')}"
            elif not isinstance(value, dict) or not isinstance(value.get("status"), str) or value["status"] not in STATUSES or not isinstance(value.get("detail"), str) or not value["detail"].strip():
                raise ValueError(f"{key}.{identifier}: require status and nonempty detail")
            else:
                status, detail = value["status"], value["detail"]
                # The common task and original-value checks apply to every published page.
                if identifier in {"intent", "original_value", "completion"} and status == "not_applicable":
                    raise ValueError(f"{key}.{identifier}: core content checks cannot be not_applicable")
            findings.append({"status": status, "location": location, "item": identifier,
                             "detail": detail, "source": item["source"], "date": item["date"],
                             "period": item["period"], "scope": item["scope"]})
    return findings


def summarize(checks):
    """Give each page equal influence within a criterion. Retain unknown fractions."""
    totals = defaultdict(lambda: {"applicable_weight": 0.0, "measured_weight": 0.0, "earned_weight": 0.0})
    for check in checks:
        grouped = defaultdict(list)
        for finding in check["findings"]:
            if finding["status"] != "not_applicable":
                grouped[finding["location"]].append(finding)
        statuses = [f["status"] for f in check["findings"]]
        applicable = bool(grouped) or not statuses
        measured = earned = 0.0
        for rows in grouped.values():
            measured += sum(f["status"] in {"pass", "fail"} for f in rows) / len(rows)
            earned += sum(f["status"] == "pass" for f in rows) / len(rows)
        if grouped:
            measured /= len(grouped)
            earned /= len(grouped)
        check.update({"passed": statuses.count("pass"), "total": len(statuses),
                      "unmeasured": statuses.count("unmeasured"),
                      "not_applicable": statuses.count("not_applicable"),
                      "applicable_weight": check["weight"] if applicable else 0,
                      "measured_weight": check["weight"] * measured,
                      "earned_weight": check["weight"] * earned,
                      "status": "fail" if "fail" in statuses else "not_applicable" if not applicable else
                      "unmeasured" if not measured else "partial" if measured < 1 else "pass"})
        for target in (totals["all"], totals[check["category"]]):
            for field in ("applicable_weight", "measured_weight", "earned_weight"):
                target[field] += check[field]

    def result(values):
        applicable, measured, earned = (values[k] for k in ("applicable_weight", "measured_weight", "earned_weight"))
        return {**{k: round(v, 4) for k, v in values.items()},
                "score": round(100 * earned / measured) if measured else None,
                "coverage": round(100 * measured / applicable, 2) if applicable else None,
                "score_bounds": {"lower": round(100 * earned / applicable, 2),
                                 "upper": round(100 * (earned + applicable - measured) / applicable, 2)} if applicable else None,
                "complete": bool(applicable) and abs(applicable - measured) < 1e-8}

    overall = result(totals.pop("all"))
    return {**overall, "scoring_version": SCORING_VERSION,
            "category_scores": {category: result(values) for category, values in totals.items()},
            "not_evaluated": [c["id"] for c in checks if c["measured_weight"] < c["applicable_weight"]],
            "critical_failures": [{"check": c["id"], **f} for c in checks
                                  if c["id"] in {"technical.robots", "technical.indexing", "technical.http"}
                                  for f in c["findings"] if f["status"] == "fail"]}


def refresh_report(report):
    report.update(summarize(report["checks"]))
    report["not_evaluated"] += ["external evidence authenticity", "rich result eligibility"]
    # Page assessments deliberately exclude site-wide and unmatched account evidence.
    report["page_assessments"] = []
    locations = {}
    for check in report["checks"]:
        grouped = defaultdict(list)
        for finding in check["findings"]:
            grouped[finding["location"]].append(finding)
        locations[check["id"]] = grouped
    for url, location in report.get("page_locations", {}).items():
        checks = []
        for check in report["checks"]:
            if check["id"] == "offpage.review":
                continue
            rows = [finding for key in {url, location} for finding in locations[check["id"]].get(key, [])]
            if rows or check["id"] in {"onpage.intent_review", "geo.review", "technical.indexing",
                                       "performance.lcp", "performance.inp", "performance.cls"}:
                checks.append({"id": check["id"], "category": check["category"], "weight": check["weight"],
                               "findings": deepcopy(rows)})
        report["page_assessments"].append({"url": url, "location": location, **summarize(checks), "checks": checks,
                                           "page_type": report.get("page_types", {}).get(url),
                                           "scope": "page evidence only, site-wide checks excluded"})
    return report

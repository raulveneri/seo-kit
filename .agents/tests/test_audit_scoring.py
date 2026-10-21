import copy
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit import audit, compare
from audit_scoring import CONTENT_COMMON, summarize

ORIGIN = "https://example.org"


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.page("index.html", "Home", "/", '<a href="/guide/">Guide</a>')
        self.page("guide/index.html", "Guide", "/guide/", '<a href="/">Home</a>')
        (self.root / "robots.txt").write_text("User-agent: *\nAllow: /\n")

    def page(self, file, title, canonical, body="", extra=""):
        target = self.root / file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f'<html lang="en"><head><title>{title}</title>'
                          f'<meta name="description" content="{"Description " * 20}">'
                          f'<link rel="canonical" href="{canonical}">'
                          f'<meta name="viewport" content="width=device-width">{extra}</head>'
                          f'<body><h1>{title}</h1>{body}</body></html>')

    def evidence(self, **fields):
        return {"source": "dated project review", "date": "2026-01-01", "period": "reviewed version",
                "scope": ORIGIN, **fields}

    def check(self, report, key):
        return next(c for c in report["checks"] if c["id"] == key)

    def test_length_multiple_h1_and_alternate_canonical_do_not_create_false_failures(self):
        self.page("guide/index.html", "A descriptive title " * 8, "/",
                  '<h1>Another section heading</h1><a href="/">Home</a>')
        report = audit(self.root, ORIGIN)
        for key in ("onpage.title", "onpage.description", "onpage.heading_one", "technical.canonical"):
            self.assertEqual(self.check(report, key)["status"], "pass", key)
        self.assertEqual(self.check(report, "technical.sitemap")["status"], "unmeasured")
        self.assertEqual(self.check(report, "technical.structured_data")["status"], "not_applicable")

    def test_googlebot_policy_checks_page_paths_and_specific_groups(self):
        (self.root / "robots.txt").write_text("User-agent: *\nAllow: /\nUser-agent: Googlebot\nDisallow: /guide/\n")
        report = audit(self.root, ORIGIN)
        self.assertEqual(self.check(report, "technical.robots")["passed"], 1)
        self.assertTrue(any(f["location"] == "guide/index.html" for f in report["critical_failures"]))

    def test_sitemap_can_be_a_subset_but_must_not_submit_known_noindex_pages(self):
        sitemap = self.root / "sitemap.xml"
        sitemap.write_text(f'<urlset><url><loc>{ORIGIN}/</loc></url></urlset>')
        self.assertEqual(self.check(audit(self.root, ORIGIN), "technical.sitemap")["status"], "pass")
        self.page("index.html", "Home", "/", extra='<meta name="robots" content="none">')
        self.assertEqual(self.check(audit(self.root, ORIGIN), "technical.sitemap")["status"], "fail")

    def test_blanket_verdict_has_no_qualitative_credit(self):
        report = audit(self.root, ORIGIN, {"checks": {
            "onpage.intent_review": self.evidence(status="pass", detail="All content looks good"),
            "geo.review": self.evidence(status="pass", detail="Ready for AI"),
        }})
        for key in ("onpage.intent_review", "geo.review"):
            self.assertEqual(self.check(report, key)["measured_weight"], 0)
        self.assertFalse(report["complete"])
        self.assertLess(report["score_bounds"]["lower"], report["score"])
        report = audit(self.root, ORIGIN, {"checks": {"onpage.intent_review": None}})
        self.assertEqual(self.check(report, "onpage.intent_review")["measured_weight"], 0)

    def test_reviewed_page_does_not_pass_unreviewed_page_and_guide_tasks_are_required(self):
        items = {key: {"status": "pass", "detail": "Inspected fixture evidence"} for key in CONTENT_COMMON}
        review = self.evidence(pages={ORIGIN + "/guide/": {"page_type": "guide", "items": items}})
        report = audit(self.root, ORIGIN, {"checks": {"onpage.intent_review": review}})
        check = self.check(report, "onpage.intent_review")
        self.assertAlmostEqual(check["measured_weight"], 7 * .8 / 2)
        self.assertEqual(check["status"], "partial")
        page = next(p for p in report["page_assessments"] if p["url"].endswith("/guide/"))
        self.assertEqual(page["page_type"], "guide")
        self.assertEqual(self.check(page, "onpage.intent_review")["unmeasured"], 2)
        self.assertNotIn("offpage.review", [c["id"] for c in page["checks"]])
        review["pages"][ORIGIN + "/guide/"]["items"]["instructions"] = {"status": "fail", "detail": "The documented command fails on the reviewed version"}
        failed = audit(self.root, ORIGIN, {"checks": {"onpage.intent_review": review}})
        self.assertEqual(self.check(failed, "onpage.intent_review")["status"], "fail")

    def test_unknown_items_pages_and_inapplicable_core_tasks_are_rejected(self):
        for pages in (
            {ORIGIN + "/outside/": {}},
            {ORIGIN + "/": {"items": {"invented": {"status": "pass", "detail": "fixture"}}}},
            {ORIGIN + "/": {"items": {"intent": {"status": "not_applicable", "detail": "fixture"}}}},
            {ORIGIN + "/": {"page_type": []}},
        ):
            with self.assertRaises(ValueError):
                audit(self.root, ORIGIN, {"checks": {"onpage.intent_review": self.evidence(pages=pages)}})
        with self.assertRaisesRegex(ValueError, "require status"):
            audit(self.root, ORIGIN, {"checks": {"geo.review": self.evidence(items={
                "access": {"status": [], "detail": "Invalid input must produce a validation error"}})}})

    def test_page_counts_do_not_let_many_links_hide_another_pages_failure(self):
        findings = [{"location": "home", "status": "pass"}] * 100 + [{"location": "guide", "status": "fail"}]
        summary = summarize([{"id": "onpage.link_text", "category": "onpage", "weight": 3, "findings": findings}])
        self.assertEqual(summary["score"], 50)
        self.assertEqual(summary["coverage"], 100)

    def test_nan_infinite_and_boolean_field_values_are_rejected(self):
        for value in (math.nan, math.inf, -math.inf, True):
            with self.assertRaises(ValueError):
                audit(self.root, ORIGIN, {"checks": {"performance.lcp": self.evidence(kind="field_p75", value=value)}})

    def test_no_applicable_items_do_not_manufacture_a_perfect_score(self):
        summary = summarize([{"id": "onpage.image_alt", "category": "onpage", "weight": 3,
                              "findings": [{"location": "home", "status": "not_applicable"}]}])
        self.assertIsNone(summary["score"])
        self.assertIsNone(summary["coverage"])
        self.assertFalse(summary["complete"])

    def test_conflicting_and_hostless_canonical_declarations_fail(self):
        self.page("guide/index.html", "Guide", "https:///", extra='<link rel="canonical" href="/guide/">')
        self.assertEqual(self.check(audit(self.root, ORIGIN), "technical.canonical")["status"], "fail")

    def test_changed_rubric_or_measurement_set_prevents_numeric_comparison(self):
        report = audit(self.root, ORIGIN)
        old = copy.deepcopy(report)
        old.pop("scoring_version")
        self.assertIsNone(compare(report, old)["score_delta"])
        old = copy.deepcopy(report)
        old["checks"][0]["findings"][0]["status"] = "unmeasured"
        self.assertIsNone(compare(report, old)["score_delta"])
        self.assertEqual(compare(report, copy.deepcopy(report))["score_delta"], 0)


if __name__ == "__main__":
    unittest.main()

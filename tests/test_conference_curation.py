"""Curation guardrails: preserve legitimate, source-grounded conference records."""
import json
from pathlib import Path
import unittest
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
KNOWN_UNTRUSTED = (
    "allconferencealert", "conferencealerts", "internationalconference",
    "eventbrite.com", "10times.com", "conferencenext"
)
FLAGSHIP_IDS = {
    "aan27", "aacr27", "asco27", "aan27", "sgim27",
    "ean27", "eau27", "aao-hns27", "aao-oph27",
    "aua-urology27", "vam27"
}

class ConferenceCurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/"data.json").read_text(encoding="utf-8"))
        cls.conferences=cls.data["conferences"]

    def test_identifiable_organizers_and_official_sources(self):
        for c in self.conferences:
            with self.subTest(c.get("id")):
                self.assertTrue(c.get("id") and c.get("name") and c.get("society"))
                url=urlparse(c.get("url") or "")
                self.assertEqual(url.scheme, "https")
                self.assertTrue(url.hostname)
                self.assertFalse(any(unsafe in url.hostname for unsafe in KNOWN_UNTRUSTED))

    def test_unique_records_and_no_rolled_forward_dates(self):
        ids=[c["id"] for c in self.conferences]
        self.assertEqual(len(ids),len(set(ids)))
        for c in self.conferences:
            with self.subTest(c["id"]):
                if c.get("start") and c.get("end"):
                    self.assertLessEqual(c["start"],c["end"])
                if c.get("deadline") and c.get("start"):
                    self.assertLessEqual(c["deadline"],c["start"])
                if c.get("evidence")=="unannounced":
                    self.assertIsNone(c.get("start"))
                    self.assertIsNone(c.get("end"))

    def test_browser_dataset_in_sync(self):
        js=(ROOT/"data.js").read_text(encoding="utf-8")
        prefix="window.RISE_DATA = "
        self.assertIn(prefix,js)
        browser=json.loads(js.split(prefix,1)[1].rstrip().removesuffix(";"))
        self.assertEqual(browser,self.data)

    def test_major_scientific_conferences_not_accidentally_removed(self):
        ids={c["id"] for c in self.conferences}
        self.assertTrue({"ean27","eau27","aao-hns27","aao-oph27","aua-urology27","vam27"}.issubset(ids))

    def test_restricted_conference_is_disclosed(self):
        acnp=next(c for c in self.conferences if c["id"]=="acnp27")
        self.assertTrue("invit" in (acnp.get("note") or "").lower())

    def test_verified_submissions_are_not_inferred_from_names(self):
        for c in self.conferences:
            with self.subTest(c["id"]):
                if c.get("submissionCategoriesVerified"):
                    self.assertTrue(c.get("url"))
                    self.assertTrue(c.get("types") or c.get("presentationFormats"))

if __name__=="__main__":
    unittest.main()

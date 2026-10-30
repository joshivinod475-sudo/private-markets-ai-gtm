import json
import unittest
from pathlib import Path

import yaml

from gtm.models import AccountBrief
from gtm.pipeline import pick_contacts
from gtm.render import brief_to_markdown
from gtm.scoring import account_score, match_persona

CONFIG = yaml.safe_load(Path("config/icp.yaml").read_text(encoding="utf-8"))
PERSONAS = CONFIG["personas"]
SAMPLE = json.loads(Path("data/sample_accounts.json").read_text(encoding="utf-8"))


def brief(**overrides):
    return AccountBrief.model_validate({**SAMPLE[0]["brief"], **overrides})


class PersonaTest(unittest.TestCase):
    def test_longest_title_wins(self):
        self.assertEqual(match_persona("Operating Partner", PERSONAS)["agent"], "Portfolio Monitoring Agent")
        self.assertEqual(match_persona("Managing Partner", PERSONAS)["agent"], "Deal Sourcing Agent")

    def test_associate_gets_diligence_agent(self):
        self.assertEqual(match_persona("Senior Associate, Healthcare", PERSONAS)["agent"], "Diligence Agent")

    def test_unrelated_title_is_skipped(self):
        self.assertIsNone(match_persona("Executive Assistant", PERSONAS))

    def test_one_contact_per_persona(self):
        picked = pick_contacts(SAMPLE[0]["contacts"], PERSONAS, limit=3)
        self.assertEqual([c["first_name"] for c in picked], ["Dana", "Marcus", "Rina"])  # Tom duplicates Dana's persona


class ScoringTest(unittest.TestCase):
    def test_sourced_signals_raise_score(self):
        self.assertEqual(account_score(brief()), 91)  # 0.6*85 + 3*10 + 10

    def test_unsourced_signals_do_not_count(self):
        unsourced = [dict(s, source_url="") for s in SAMPLE[0]["brief"]["recent_signals"]]
        self.assertEqual(account_score(brief(recent_signals=unsourced)), 61)

    def test_score_capped_at_100(self):
        self.assertEqual(account_score(brief(fit_score=100)), 100)


class RenderTest(unittest.TestCase):
    def test_markdown_keeps_sources_and_caveats(self):
        md = brief_to_markdown(brief(), 91)
        self.assertIn("[source](https://harborline.example/news/fund-iii)", md)
        self.assertIn("## Could not verify", md)


if __name__ == "__main__":
    unittest.main()

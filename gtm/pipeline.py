"""Account-based run: firms -> research agent -> score -> contacts by persona -> messages -> export -> push."""
import csv
import json
import os
import re
from datetime import date
from pathlib import Path

from .apollo import Apollo, to_contact, to_firm
from .models import AccountBrief
from .render import brief_to_markdown
from .saleshandy import Saleshandy
from .scoring import account_score, match_persona

OUTPUT = Path("output")
SEEN_FILE = OUTPUT / "seen_firms.json"
CSV_COLUMNS = ["account_score", "company", "first_name", "last_name", "email", "title", "persona",
               "agent", "subject", "first_line", "agent_pitch", "firm_insight"]


def _slug(text):
    return re.sub(r"\W+", "-", text.lower()).strip("-")


def _save(accounts):
    """Write one Markdown brief per account plus a single contacts CSV."""
    briefs_dir = OUTPUT / "briefs"
    briefs_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for brief, score, contacts in accounts:
        (briefs_dir / f"{_slug(brief.firm_name)}.md").write_text(
            brief_to_markdown(brief, score, contacts), encoding="utf-8")
        rows += [{**c, "account_score": score} for c in contacts]
    path = OUTPUT / f"contacts_{date.today():%Y%m%d}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return briefs_dir, path, rows


def pick_contacts(people, personas, limit):
    """One contact per persona, best personas first, up to `limit`."""
    chosen, used = [], set()
    for person in people:
        persona = match_persona(person.get("title", ""), personas)
        if persona and persona["name"] not in used:
            chosen.append({**person, "persona": persona["name"], "agent": persona["agent"], "pain": persona["pain"]})
            used.add(persona["name"])
        if len(chosen) == limit:
            break
    return chosen


def run(config, live=False, accounts=5):
    from .research import Researcher  # needs ANTHROPIC_API_KEY

    OUTPUT.mkdir(exist_ok=True)
    seen = set(json.loads(SEEN_FILE.read_text())) if SEEN_FILE.exists() else set()
    apollo = Apollo(os.environ["APOLLO_API_KEY"])
    researcher = Researcher(config)
    personas = config["personas"]
    all_titles = [t for p in personas for t in p["titles"]]

    print("1/5 Finding firms in Apollo...")
    firms = [to_firm(o) for o in apollo.search_firms(config["apollo_accounts"])]
    firms = [f for f in firms if f["apollo_id"] not in seen][:accounts]
    print(f"    researching {len(firms)} new firms")

    results = []
    for firm in firms:
        print(f"2/5 Research agent: {firm['name']}...")
        brief = researcher.brief(firm)
        score = account_score(brief)
        print(f"    score {score}/100, {len(brief.recent_signals)} sourced signals")
        if score < config["scoring"]["min_score"]:
            results.append((brief, score, []))
            continue

        print("3/5 Finding the right people...")
        people = apollo.search_people(firm["apollo_id"], all_titles, per_page=25)
        picked = pick_contacts(people, personas, config["contacts_per_account"])
        enriched = {p["id"]: p for p in apollo.enrich([p["id"] for p in picked])}
        contacts = []
        for p in picked:
            if p["id"] in enriched and enriched[p["id"]].get("email"):
                contacts.append({**to_contact(enriched[p["id"]]), "company": firm["name"],
                                 "persona": p["persona"], "agent": p["agent"], "pain": p["pain"],
                                 "firm_insight": brief.angle})

        if contacts:
            print("4/5 Writing role-specific messages...")
            written = researcher.messages(brief, contacts)
            for c in contacts:
                m = written.get(c["email"])
                if m:
                    c.update(subject=m.subject, first_line=m.first_line, agent_pitch=m.agent_pitch)
        results.append((brief, score, contacts))

    briefs_dir, csv_path, rows = _save(results)
    print(f"    Briefs in {briefs_dir}/, contacts in {csv_path}")

    if not live:
        print("5/5 Dry run: nothing sent. Review the briefs and CSV, then rerun with --live.")
        return
    print("5/5 Adding contacts to Saleshandy...")
    saleshandy = Saleshandy(os.environ["SALESHANDY_API_KEY"])
    ready = [r for r in rows if r.get("first_line")]
    for email, status in saleshandy.import_contacts(ready, os.environ["SALESHANDY_STEP_ID"],
                                                    config["saleshandy"]).items():
        print(f"    {email}: {status}")
    seen.update(f["apollo_id"] for f in firms)
    SEEN_FILE.write_text(json.dumps(sorted(seen)))


def demo(config):
    """Render briefs and template messages from fictional sample accounts. No API keys needed."""
    sample = json.loads(Path("data/sample_accounts.json").read_text(encoding="utf-8"))
    results = []
    for account in sample:
        brief = AccountBrief.model_validate(account["brief"])
        score = account_score(brief)
        contacts = []
        for c in pick_contacts(account["contacts"], config["personas"], config["contacts_per_account"]):
            contacts.append({**c, "company": brief.firm_name, "firm_insight": brief.angle,
                             "subject": f"{brief.firm_name.split()[0].lower()} and {c['agent'].lower()}",
                             "first_line": brief.angle,
                             "agent_pitch": f"Our {c['agent']} is built for {c['pain']}."})
        results.append((brief, score, contacts))
        print(f"{brief.firm_name}: score {score}/100, {len(contacts)} contacts")
        for c in contacts:
            print(f"   {c['first_name']} ({c['title']}) -> {c['agent']}")
    briefs_dir, csv_path, _ = _save(results)
    print(f"\nBriefs in {briefs_dir}/, contacts in {csv_path}")

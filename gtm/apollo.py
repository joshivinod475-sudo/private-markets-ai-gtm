"""Apollo.io: find firms and people (free search) and reveal work emails (uses credits)."""
import time

import requests

BASE_URL = "https://api.apollo.io/api/v1"


class Apollo:
    def __init__(self, api_key):
        self.session = requests.Session()
        self.session.headers.update({
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        })

    def _post(self, path, body):
        for attempt in range(4):
            resp = self.session.post(f"{BASE_URL}{path}", json=body, timeout=60)
            if resp.status_code == 429:  # rate limited: wait and retry
                time.sleep(2 ** attempt * 5)
                continue
            resp.raise_for_status()
            return resp.json()
        resp.raise_for_status()

    def search_firms(self, filters, page=1):
        data = self._post("/mixed_companies/search", {**filters, "page": page})
        return data.get("organizations") or data.get("accounts") or []

    def search_people(self, org_id, titles, per_page=5):
        data = self._post("/mixed_people/api_search", {
            "organization_ids": [org_id],
            "person_titles": titles,
            "per_page": per_page,
            "page": 1,
        })
        return data.get("people", [])

    def enrich(self, person_ids):
        """Reveal emails, 10 people per call. Costs Apollo credits."""
        results = []
        for i in range(0, len(person_ids), 10):
            batch = [{"id": pid} for pid in person_ids[i:i + 10]]
            data = self._post("/people/bulk_match", {"details": batch, "reveal_personal_emails": False})
            results.extend(m for m in data.get("matches", []) if m)
        return results


def to_firm(org):
    return {
        "apollo_id": org.get("id", ""),
        "name": org.get("name", ""),
        "website": org.get("website_url") or org.get("primary_domain") or "",
        "city": org.get("city") or "",
        "employees": org.get("estimated_num_employees") or 0,
        "linkedin": org.get("linkedin_url") or "",
    }


def to_contact(person):
    return {
        "first_name": person.get("first_name", ""),
        "last_name": person.get("last_name", ""),
        "email": person.get("email") or "",
        "email_status": person.get("email_status") or "",
        "title": person.get("title") or "",
        "linkedin": person.get("linkedin_url") or "",
    }

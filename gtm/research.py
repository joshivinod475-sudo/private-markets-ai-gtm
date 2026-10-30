"""The research agent: Claude searches the web about one firm and returns a sourced account brief."""
import json

import anthropic

from .models import AccountBrief, AccountMessages

MODEL = "claude-opus-5-5"
BETAS = ["server-side-fallback-2026-07-01"]
MAX_CONTINUATIONS = 5

TOOLS = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 6},
    {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 4},
]

RESEARCH_SYSTEM = """You are a research analyst preparing an account brief for a B2B sales team
that sells AI agents to private equity firms, transaction advisors and investment banks.

Research the firm using its website and recent public sources. Find:
- What kind of firm it is, its strategy, target sectors and typical check size.
- Its latest fund (name, size, close date) or AUM, if public.
- Signals from the last 18 months: fund closes, new platform investments, add-ons,
  exits, senior hires (especially deal team, operating partners, data/AI roles),
  and any AI or technology initiatives.

Rules: only report what sources support, and give a URL for every signal. Say
clearly when something could not be found. Do not guess fund sizes or dates."""

STRUCTURE_PROMPT = """Turn these research notes into the account brief schema.
Only use facts in the notes; keep each signal's source URL. Use "" for unknowns.

Score fit_score 0-100 for this product: {product}
Higher when the firm is a PE firm, transaction advisor or investment bank, is
actively deploying capital (recent fund or deals), has a sector thesis that
benefits from systematic target sourcing, or shows interest in AI.
recommended_agents must come from: {agents}.

Firm: {firm}

Research notes:
{notes}"""

MESSAGES_SYSTEM = """You write short, specific cold emails to private markets professionals.
For each contact write:
- subject: max 6 words, lowercase, no hype.
- first_line: one sentence referencing a real, sourced detail from the brief that is relevant
  to this person's role. Never invent facts.
- agent_pitch: one or two sentences connecting the named agent to this
  person's day-to-day pain. Concrete, no buzzwords, no exaggerated claims."""


class Researcher:
    def __init__(self, config):
        self.client = anthropic.Anthropic()
        self.product = config["product"]
        self.agents = sorted({p["agent"] for p in config["personas"]})

    def _create(self, **kwargs):
        return self.client.beta.messages.create(
            model=MODEL, betas=BETAS, fallbacks="default", **kwargs)

    def research(self, firm):
        """Let Claude search and read the web, then return its notes plus source URLs."""
        question = f"Research this firm: {json.dumps(firm)}"
        messages = [{"role": "user", "content": question}]
        for _ in range(MAX_CONTINUATIONS + 1):
            response = self._create(
                max_tokens=16000, system=RESEARCH_SYSTEM, tools=TOOLS,
                output_config={"effort": "medium"}, messages=messages)
            if response.stop_reason != "pause_turn":
                break
            # long research turns pause; send the partial turn back to continue it
            messages = [{"role": "user", "content": question},
                        {"role": "assistant", "content": response.content}]
        if response.stop_reason == "refusal":
            raise RuntimeError("research request was declined")

        notes, sources = [], []
        for block in response.content:
            if block.type == "text":
                notes.append(block.text)
                sources += [c.url for c in (block.citations or []) if getattr(c, "url", None)]
        unique_sources = list(dict.fromkeys(sources))
        return "\n".join(notes) + "\n\nSources:\n" + "\n".join(unique_sources)

    def brief(self, firm):
        notes = self.research(firm)
        response = self.client.beta.messages.parse(
            model=MODEL, betas=BETAS, fallbacks="default", max_tokens=8000,
            output_config={"effort": "low"}, output_format=AccountBrief,
            messages=[{"role": "user", "content": STRUCTURE_PROMPT.format(
                product=self.product["one_liner"], agents=", ".join(self.agents),
                firm=json.dumps(firm), notes=notes)}])
        if response.stop_reason == "refusal":
            raise RuntimeError("brief request was declined")
        return response.parsed_output

    def messages(self, brief, contacts):
        people = [{k: c[k] for k in ("email", "first_name", "title", "persona", "agent", "pain")}
                  for c in contacts]
        response = self.client.beta.messages.parse(
            model=MODEL, betas=BETAS, fallbacks="default", max_tokens=8000,
            system=MESSAGES_SYSTEM, output_config={"effort": "medium"}, output_format=AccountMessages,
            messages=[{"role": "user", "content":
                       f"Product: {self.product['name']}: {self.product['one_liner']}\n\n"
                       f"Account brief:\n{brief.model_dump_json(indent=2)}\n\n"
                       f"Contacts:\n{json.dumps(people, indent=2)}"}])
        if response.stop_reason == "refusal":
            raise RuntimeError("message request was declined")
        return {m.email: m for m in response.parsed_output.messages}

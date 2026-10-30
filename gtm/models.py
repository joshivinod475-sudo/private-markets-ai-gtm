"""Shapes for the research agent's account brief and the per-contact messages."""
from pydantic import BaseModel


class Signal(BaseModel):
    kind: str          # e.g. fund close, new platform deal, add-on, exit, key hire, AI initiative
    summary: str
    date: str          # as precise as the source allows, "" if unknown
    source_url: str


class AccountBrief(BaseModel):
    firm_name: str
    website: str
    segment: str       # private_equity | transaction_advisory | investment_bank | other
    strategy: str      # e.g. lower middle-market buyout, growth equity
    sectors: list[str]
    check_size: str
    fund_info: str     # latest fund / AUM if public, "" if unknown
    recent_signals: list[Signal]
    fit_score: int     # 0-100, Claude's view of fit for the product
    fit_reasons: list[str]
    recommended_agents: list[str]
    angle: str         # the one insight to open with
    caveats: list[str] # what couldn't be verified


class ContactMessage(BaseModel):
    email: str
    subject: str
    first_line: str
    agent_pitch: str


class AccountMessages(BaseModel):
    messages: list[ContactMessage]

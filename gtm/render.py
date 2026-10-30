"""Turn an account brief into a one-page Markdown file a sales rep can read in two minutes."""


def brief_to_markdown(brief, score, contacts=()):
    lines = [
        f"# {brief.firm_name}",
        "",
        f"**Account score: {score}/100** · {brief.segment.replace('_', ' ')} · {brief.website}",
        "",
        "## Snapshot",
        f"- **Strategy:** {brief.strategy or 'unknown'}",
        f"- **Sectors:** {', '.join(brief.sectors) or 'unknown'}",
        f"- **Check size:** {brief.check_size or 'unknown'}",
        f"- **Latest fund / AUM:** {brief.fund_info or 'not public'}",
        "",
        "## Recent signals",
    ]
    lines += [f"- **{s.kind}** ({s.date or 'date unknown'}): {s.summary} [source]({s.source_url})"
              for s in brief.recent_signals] or ["- None found in public sources"]
    lines += ["", "## Why they fit", *[f"- {r}" for r in brief.fit_reasons],
              "", "## Opening angle", brief.angle,
              "", "## Agents to lead with", *[f"- {a}" for a in brief.recommended_agents]]
    if contacts:
        lines += ["", "## Contacts", "", "| Name | Title | Pitch | Opener |", "|---|---|---|---|"]
        lines += [f"| {c['first_name']} {c['last_name']} | {c['title']} | {c['agent']} | {c['first_line']} |"
                  for c in contacts]
    if brief.caveats:
        lines += ["", "## Could not verify", *[f"- {c}" for c in brief.caveats]]
    return "\n".join(lines) + "\n"

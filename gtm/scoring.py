"""Account scoring and persona matching."""


def account_score(brief):
    """Blend Claude's fit view with hard evidence: segment and sourced recent signals."""
    score = 0.6 * brief.fit_score
    score += 10 * min(len([s for s in brief.recent_signals if s.source_url]), 3)
    if brief.segment == "private_equity":
        score += 10
    return min(round(score), 100)


def match_persona(title, personas):
    """Pick the persona whose matching title is longest, so 'Operating Partner'
    beats 'Partner'. Returns None when nothing matches."""
    title = title.lower()
    best, best_len = None, 0
    for persona in personas:
        for t in persona["titles"]:
            if t.lower() in title and len(t) > best_len:
                best, best_len = persona, len(t)
    return best

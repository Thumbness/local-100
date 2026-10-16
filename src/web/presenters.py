def ordinal(n: int) -> str:
    """Format an integer as an ordinal, e.g. 1 -> 1st, 112 -> 112th."""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


def countdown_view(playable) -> dict:
    """Shape a PlayableEntry for the countdown page."""
    entry = playable.entry
    return {
        "filename": playable.filename,
        "title": entry.title,
        "artist": entry.artist,
        "rank": ordinal(entry.rank),
        "points": entry.points,
        "voters": [{"name": v.name, "position": ordinal(v.position)} for v in entry.voters],
    }

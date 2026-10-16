from ...domain.countdown.entry import CountdownEntry, Voter


class CountdownFileFormat:
    """Reads the raw countdown export: a list of entries, or the {"results": {"countdownResults": [...]}} wrapper."""

    def check(self, raw) -> str | None:
        items = _items(raw)
        if items is None:
            return "Unrecognised format. Expected a list of countdown entries."
        if not items:
            return "The file has no countdown entries."
        return None

    def parse(self, raw) -> list[CountdownEntry]:
        return [_entry(item) for item in _items(raw)]


def _items(raw):
    if isinstance(raw, list):
        return raw
    try:
        return raw["results"]["countdownResults"]
    except (TypeError, KeyError):
        return None


def _entry(item: dict) -> CountdownEntry:
    return CountdownEntry(
        title=item.get("name"),
        artist=(item.get("artists") or [{}])[0].get("name"),
        rank=item.get("songRank"),
        points=item.get("points"),
        youtube_url=_as_https(item.get("youtubeUrl")),
        voters=tuple(Voter(name=v.get("name"), position=v.get("position", 0))
                     for v in item.get("voters", [])),
    )


def _as_https(url: str | None) -> str:
    if not url:
        return ""
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("http://"):
        return "https://" + url[len("http://"):]
    if not url.startswith("https://"):
        return "https://" + url.lstrip("/")
    return url

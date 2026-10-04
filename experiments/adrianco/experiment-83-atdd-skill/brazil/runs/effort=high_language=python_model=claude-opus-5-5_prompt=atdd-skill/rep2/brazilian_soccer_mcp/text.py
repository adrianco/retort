"""
Text and date helpers shared by the datasets and the query engine.

- plain(): accent- and case-insensitive form of a name ("Grêmio" -> "gremio"),
  so questions match data whichever way either is written.
- parse_date(): understands every date format in the provided datasets
  (ISO "2023-09-24", ISO with time "2012-05-19 18:30:00", Brazilian
  "29/03/2003") and returns a datetime.date, or None if absent/unparseable.
"""
import datetime
import re
import unicodedata

_PUNCTUATION = re.compile(r"[^a-z0-9]+")
_SPACED_INITIALS = re.compile(r"\b(?:[a-z] ){1,}[a-z]\b")


def strip_accents(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def plain(text):
    """Lower-case, accent-free, punctuation-free; initials like 'C. R. B.' become 'crb'."""
    text = _PUNCTUATION.sub(" ", strip_accents(text or "").lower()).strip()
    return _SPACED_INITIALS.sub(lambda m: m.group(0).replace(" ", ""), text)


def has_accents(text):
    return strip_accents(text) != text


def parse_date(value):
    value = (value or "").strip()
    if not value or value.upper() == "NA":
        return None
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def parse_int(value):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None

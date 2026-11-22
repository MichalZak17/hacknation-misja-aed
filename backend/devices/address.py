"""Splits an address line ("ul. Marszałkowska 126/134") into street prefix (cecha), street name and building number,
the separate fields dane.gov.pl asks for. A deterministic split of what the source wrote: a missing prefix stays empty
rather than being guessed as "ul."."""

import re

# Spellings sources use → the abbreviation dane.gov.pl's "cecha adresu" check accepts
STREET_TYPES = {
    "ul.": "ul.",
    "ul": "ul.",
    "ulica": "ul.",
    "al.": "al.",
    "al": "al.",
    "aleja": "al.",
    "aleje": "al.",
    "pl.": "pl.",
    "pl": "pl.",
    "plac": "pl.",
    "os.": "os.",
    "osiedle": "os.",
    "rondo": "rondo",
    "skwer": "skwer",
    "bulw.": "bulw.",
    "bulwar": "bulw.",
    "park": "park",
    "rynek": "rynek",
    "szosa": "szosa",
    "droga": "droga",
    "wyb.": "wyb.",
    "wybrzeże": "wyb.",
}
# A building number at the end: 5, 5a, 12-14, 126/134, 5A/2
NUMBER = re.compile(r"^(?P<street>.*?\S)\s+(?P<number>\d+\s*[A-Za-z]?(?:\s*[/-]\s*\d+\s*[A-Za-z]?)*)$")


def split_address(address: str | None) -> tuple[str | None, str | None, str | None]:
    """'ul. Marszałkowska 126/134' → ('ul.', 'Marszałkowska', '126/134'); 'Rynek 1' → ('rynek', 'Rynek', '1')."""
    text = " ".join((address or "").split())
    if not text:
        return None, None, None
    street, number = text, None
    match = NUMBER.match(text)
    if match:
        street, number = match.group("street"), re.sub(r"\s+", "", match.group("number"))
    street_type = None
    first, _, rest = street.partition(" ")
    if first.lower() in STREET_TYPES:
        street_type = STREET_TYPES[first.lower()]
        # "ul. Rynek" drops the prefix; a bare "Rynek" or "Plac" is the name itself
        if rest:
            street = rest
    return street_type, street or None, number

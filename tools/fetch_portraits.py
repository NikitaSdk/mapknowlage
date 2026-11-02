"""Скачивает портреты с Википедии, если лицензия это позволяет."""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "portraits"
OUT.mkdir(parents=True, exist_ok=True)

TITLES = {
    "laozi": "Laozi",
    "confucius": "Confucius",
    "socrates": "Socrates",
    "plato": "Plato",
    "aristotle": "Aristotle",
    "diogenes": "Diogenes",
    "epicurus": "Epicurus",
    "cicero": "Cicero",
    "aurelius": "Marcus Aurelius",
    "augustine": "Augustine of Hippo",
    "aquinas": "Thomas Aquinas",
    "castaneda": "Carlos Castaneda",
    "gurdjieff": "George Gurdjieff",
    "tolstoy": "Leo Tolstoy",
    "dostoevsky": "Fyodor Dostoevsky",
    "descartes": "René Descartes",
    "spinoza": "Baruch Spinoza",
    "kant": "Immanuel Kant",
    "goethe": "Johann Wolfgang von Goethe",
    "hegel": "Georg Wilhelm Friedrich Hegel",
    "schopenhauer": "Arthur Schopenhauer",
    "nietzsche": "Friedrich Nietzsche",
    "heidegger": "Martin Heidegger",
    "wittgenstein": "Ludwig Wittgenstein",
    "kierkegaard": "Søren Kierkegaard",
    "sartre": "Jean-Paul Sartre",
    "camus": "Albert Camus",
    "frankl": "Viktor Frankl",
    "machiavelli": "Niccolò Machiavelli",
    "hobbes": "Thomas Hobbes",
    "locke": "John Locke",
    "rousseau": "Jean-Jacques Rousseau",
    "marx": "Karl Marx",
    "ortega": "José Ortega y Gasset",
    "arendt": "Hannah Arendt",
    "foucault": "Michel Foucault",
    "freud": "Sigmund Freud",
    "adler": "Alfred Adler",
    "jung": "Carl Jung",
    "horney": "Karen Horney",
    "vygotsky": "Lev Vygotsky",
    "fromm": "Erich Fromm",
    "erikson": "Erik Erikson",
    "berne": "Eric Berne",
    "maslow": "Abraham Maslow",
    "rogers": "Carl Rogers",
    "hazlitt": "Henry Hazlitt",
    "smith": "Adam Smith",
    "ricardo": "David Ricardo",
    "keynes": "John Maynard Keynes",
    "hayek": "Friedrich Hayek",
    "mises": "Ludwig von Mises",
    "schumpeter": "Joseph Schumpeter",
    "friedman": "Milton Friedman",
    "graham": "Benjamin Graham",
}

OPENER = urllib.request.build_opener()
OPENER.addheaders = [("User-Agent", "MapKnowlage/1.0 (personal study map)")]


def get(url: str) -> bytes:
    import time
    import urllib.error

    for attempt in range(5):
        try:
            with OPENER.open(url, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 4:
                raise
            time.sleep(12 * (attempt + 1))
    raise RuntimeError(url)


def allowed(license_name: str) -> bool:
    low = license_name.lower()
    if any(token in low for token in ("noncommercial", "non-commercial", "-nc", "all rights reserved")):
        return False
    return any(token in low for token in ("public domain", "cc0", "cc by", "cc-by", "pdm"))


def main() -> None:
    items = list(TITLES.items())
    pages: dict[str, dict] = {}
    for offset in range(0, len(items), 20):
        chunk = dict(items[offset : offset + 20])
        query = urllib.parse.urlencode(
            {
                "action": "query",
                "titles": "|".join(chunk.values()),
                "prop": "pageimages",
                "pithumbsize": "480",
                "format": "json",
            }
        )
        payload = json.loads(get("https://en.wikipedia.org/w/api.php?" + query))
        for page in payload.get("query", {}).get("pages", {}).values():
            if page.get("title"):
                pages[page["title"]] = page

    saved = 0
    notes = []
    import time

    for author_id, title in items:
        if (OUT / f"{author_id}.png").exists():
            saved += 1
            continue
        page = pages.get(title)
        if not page or "pageimage" not in page or "thumbnail" not in page:
            print("no-image", author_id)
            continue
        file_name = page["pageimage"]
        thumb = page["thumbnail"]["source"]
        meta_query = urllib.parse.urlencode(
            {
                "action": "query",
                "titles": f"File:{file_name}",
                "prop": "imageinfo",
                "iiprop": "extmetadata",
                "format": "json",
            }
        )
        meta_payload = json.loads(get("https://en.wikipedia.org/w/api.php?" + meta_query))
        license_name = ""
        artist = ""
        for info_page in meta_payload.get("query", {}).get("pages", {}).values():
            info = (info_page.get("imageinfo") or [{}])[0]
            extra = info.get("extmetadata") or {}
            license_name = (extra.get("LicenseShortName") or {}).get("value", "")
            artist = (extra.get("Artist") or {}).get("value", "")
        if not allowed(license_name):
            print("skip-license", author_id, license_name)
            time.sleep(1.2)
            continue
        if not (OUT / f"{author_id}.png").exists():
            image = Image.open(BytesIO(get(thumb))).convert("RGB")
            image.save(OUT / f"{author_id}.png", "PNG")
        notes.append({"id": author_id, "file": file_name, "license": license_name, "artist": artist})
        saved += 1
        print("saved", author_id, license_name)
        time.sleep(1.2)
    (OUT / "attributions.json").write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
    print("total", saved)


if __name__ == "__main__":
    sys.exit(main())

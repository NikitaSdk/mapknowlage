"""Загрузка каталога из JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from mapknowlage.paths import catalog_dir


@dataclass
class Book:
    id: str
    author_id: str
    title: str
    genre: str
    order: int = 1


@dataclass
class Author:
    id: str
    name: str
    years: str
    place: str
    zone: str
    bio: str
    family: str
    genres: list[str]
    books: list[Book] = field(default_factory=list)
    group: str = ""
    x: float = 0.0
    y: float = 0.0


@dataclass
class Zone:
    id: str
    name: str
    color: str
    cx: float
    cy: float
    radius: float
    layout: str


@dataclass
class Catalog:
    zones: list[Zone]
    authors: list[Author]

    def zone(self, zone_id: str) -> Zone:
        for zone in self.zones:
            if zone.id == zone_id:
                return zone
        raise KeyError(zone_id)

    def author(self, author_id: str) -> Author:
        for author in self.authors:
            if author.id == author_id:
                return author
        raise KeyError(author_id)

    def authors_in(self, zone_id: str) -> list[Author]:
        return [author for author in self.authors if author.zone == zone_id]


def load_catalog() -> Catalog:
    folder = catalog_dir()
    zones_raw = json.loads((folder / "zones.json").read_text(encoding="utf-8"))
    authors_raw = json.loads((folder / "authors.json").read_text(encoding="utf-8"))
    books_raw = json.loads((folder / "books.json").read_text(encoding="utf-8"))

    books_by_author: dict[str, list[Book]] = {}
    for raw in books_raw:
        book = Book(
            id=raw["id"],
            author_id=raw["author_id"],
            title=raw["title"],
            genre=raw["genre"],
            order=int(raw.get("order", 1)),
        )
        owners = [book.author_id, *raw.get("also", [])]
        for owner in owners:
            books_by_author.setdefault(owner, []).append(book)

    authors = []
    for raw in authors_raw:
        books = sorted(books_by_author.get(raw["id"], []), key=lambda item: item.order)
        authors.append(
            Author(
                id=raw["id"],
                name=raw["name"],
                years=raw.get("years", ""),
                place=raw.get("place", ""),
                zone=raw["zone"],
                bio=raw.get("bio", ""),
                family=raw.get("family", ""),
                genres=list(raw.get("genres", [])),
                books=books,
                group=raw.get("group", ""),
            )
        )
    zones = [
        Zone(
            id=raw["id"],
            name=raw["name"],
            color=raw["color"],
            cx=float(raw["cx"]),
            cy=float(raw["cy"]),
            radius=float(raw["radius"]),
            layout=raw.get("layout", "ring"),
        )
        for raw in zones_raw
    ]
    return Catalog(zones=zones, authors=authors)

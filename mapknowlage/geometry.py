"""Органические зоны: точки авторов, Voronoi и шум на береговой линии."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import opensimplex
from scipy.spatial import ConvexHull, Voronoi

from mapknowlage.catalog import Author, Zone

SCENE_W = 5200.0
SCENE_H = 4900.0

# Берег начинается снаружи портрета, но не прорезает середину кольца.
AUTHOR_CLEARANCE = 160.0
HULL_PADDING = 90.0
SEA_STEP = 140.0


@dataclass
class ZoneShape:
    zone_id: str
    loops: list[list[tuple[float, float]]]
    method: str


def place_authors(zones: list[Zone], authors: list[Author]) -> None:
    grouped: dict[str, list[Author]] = defaultdict(list)
    for author in authors:
        grouped[author.zone].append(author)
    for zone in zones:
        group = grouped.get(zone.id, [])
        if zone.layout == "road":
            points = _road(len(group), zone.cx, zone.cy, zone.radius)
        else:
            points = _ring(len(group), zone.cx, zone.cy, zone.radius)
        for author, (x, y) in zip(group, points):
            author.x = x
            author.y = y


def build_zone_shapes(zones: list[Zone], authors: list[Author]) -> list[ZoneShape]:
    opensimplex.seed(14)
    grouped: dict[str, list[Author]] = defaultdict(list)
    for author in authors:
        grouped[author.zone].append(author)

    author_points = [(author.x, author.y) for author in authors]
    zone_of = [author.zone for author in authors]
    hulls = []
    for zone in zones:
        pts = [(author.x, author.y) for author in grouped.get(zone.id, [])]
        hull = _expanded_hull(pts, HULL_PADDING)
        if hull:
            hulls.append(hull)

    sea = _sea_seeds(author_points, hulls)
    sites = np.array(author_points + sea, dtype=float)
    vor = Voronoi(sites)
    n_authors = len(author_points)

    edges: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for (site_a, site_b), (vertex_a, vertex_b) in zip(vor.ridge_points, vor.ridge_vertices):
        if vertex_a < 0 or vertex_b < 0:
            continue
        zone_a = zone_of[site_a] if site_a < n_authors else None
        zone_b = zone_of[site_b] if site_b < n_authors else None
        if zone_a is not None and zone_a != zone_b:
            edges[zone_a].append((int(vertex_a), int(vertex_b)))
        if zone_b is not None and zone_b != zone_a:
            edges[zone_b].append((int(vertex_b), int(vertex_a)))

    shapes: list[ZoneShape] = []
    for zone in zones:
        group = grouped.get(zone.id, [])
        loops = _loops_from_edges(edges.get(zone.id, []), vor.vertices)
        method = "voronoi"
        if len(group) <= 2:
            loops = [_disk(zone.cx, zone.cy, max(zone.radius, 340))]
            method = "disk"
        elif not _covers(group, loops):
            loops = [_radial_blob([(author.x, author.y) for author in group])]
            method = "blob"
        shapes.append(ZoneShape(zone.id, loops, method))
    return shapes


def _ring(count: int, cx: float, cy: float, radius: float) -> list[tuple[float, float]]:
    if count <= 0:
        return []
    if count == 1:
        return [(cx, cy)]
    if count == 2:
        spread = 190.0
        return [(cx, cy - spread), (cx, cy + spread)]
    points = []
    for index in range(count):
        angle = -math.pi / 2 + 2 * math.pi * index / count
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def _road(count: int, cx: float, cy: float, half_length: float) -> list[tuple[float, float]]:
    points = []
    for index in range(count):
        t = 0.0 if count == 1 else index / (count - 1)
        x = cx + (t - 0.5) * 2 * half_length
        y = cy - math.sin(t * math.pi) * 22
        points.append((x, y))
    return points


def _expanded_hull(points: list[tuple[float, float]], padding: float) -> list[tuple[float, float]] | None:
    if len(points) < 3:
        return None
    try:
        hull = ConvexHull(np.array(points))
    except Exception:
        return None
    ordered = [points[int(index)] for index in hull.vertices]
    cx = sum(x for x, _ in ordered) / len(ordered)
    cy = sum(y for _, y in ordered) / len(ordered)
    expanded = []
    for x, y in ordered:
        dx, dy = x - cx, y - cy
        length = math.hypot(dx, dy) or 1.0
        expanded.append((x + dx / length * padding, y + dy / length * padding))
    return expanded


def _sea_seeds(
    authors: list[tuple[float, float]],
    hulls: list[list[tuple[float, float]]],
) -> list[tuple[float, float]]:
    seeds: list[tuple[float, float]] = []
    limit_x = int(SCENE_W) + 400
    limit_y = int(SCENE_H) + 400
    x = -400.0
    while x <= limit_x:
        y = -400.0
        while y <= limit_y:
            if _is_sea(x, y, authors, hulls):
                seeds.append((x, y))
            y += SEA_STEP
        x += SEA_STEP
    return seeds


def _is_sea(
    x: float,
    y: float,
    authors: list[tuple[float, float]],
    hulls: list[list[tuple[float, float]]],
) -> bool:
    clearance = AUTHOR_CLEARANCE * AUTHOR_CLEARANCE
    for ax, ay in authors:
        if (x - ax) * (x - ax) + (y - ay) * (y - ay) < clearance:
            return False
    for hull in hulls:
        if _point_in_poly(x, y, hull):
            return False
    return True


def _loops_from_edges(
    segments: list[tuple[int, int]],
    vertices: np.ndarray,
) -> list[list[tuple[float, float]]]:
    loops_idx = _stitch(segments)
    result = []
    for loop in loops_idx:
        raw = [(float(vertices[index][0]), float(vertices[index][1])) for index in loop]
        if _area(raw) < 8000:
            continue
        smooth = _chaikin(raw, 2)
        smooth = _displace(smooth, 9.0)
        smooth = _chaikin(smooth, 1)
        if _area(smooth) >= 8000:
            result.append(smooth)
    return result


def _stitch(segments: list[tuple[int, int]]) -> list[list[int]]:
    adjacency: dict[int, list[int]] = defaultdict(list)
    unused: set[tuple[int, int]] = set()
    for a, b in segments:
        if a == b:
            continue
        key = (a, b) if a < b else (b, a)
        if key in unused:
            continue
        unused.add(key)
        adjacency[a].append(b)
        adjacency[b].append(a)

    loops = []
    while unused:
        start, nxt = next(iter(unused))
        unused.remove((start, nxt) if start < nxt else (nxt, start))
        loop = [start, nxt]
        prev, current = start, nxt
        for _ in range(20000):
            follower = None
            for candidate in adjacency[current]:
                if candidate == prev:
                    continue
                key = (current, candidate) if current < candidate else (candidate, current)
                if key in unused:
                    follower = candidate
                    break
            if follower is None:
                break
            key = (current, follower) if current < follower else (follower, current)
            unused.discard(key)
            if follower == start:
                break
            loop.append(follower)
            prev, current = current, follower
        if len(loop) >= 3:
            loops.append(loop)
    return loops


def _covers(authors: list[Author], loops: list[list[tuple[float, float]]]) -> bool:
    if not authors or not loops:
        return False
    for author in authors:
        if not any(_point_in_poly(author.x, author.y, loop) for loop in loops):
            return False
    return True


def _disk(cx: float, cy: float, radius: float) -> list[tuple[float, float]]:
    steps = 56
    outline = []
    for index in range(steps):
        angle = 2 * math.pi * index / steps
        wobble = 1 + opensimplex.noise2(math.cos(angle) * 2.2, math.sin(angle) * 2.2) * 0.035
        outline.append((cx + math.cos(angle) * radius * wobble, cy + math.sin(angle) * radius * wobble))
    return outline


def _radial_blob(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not points:
        return []
    cx = sum(x for x, _ in points) / len(points)
    cy = sum(y for _, y in points) / len(points)
    outline = []
    steps = 72
    for index in range(steps):
        angle = 2 * math.pi * index / steps
        dx, dy = math.cos(angle), math.sin(angle)
        reach = 90.0
        for x, y in points:
            vx, vy = x - cx, y - cy
            forward = vx * dx + vy * dy
            side = abs(vx * -dy + vy * dx)
            portrait = 86.0
            if side < portrait:
                reach = max(reach, forward + math.sqrt(portrait * portrait - side * side) + 80)
        reach += opensimplex.noise2(dx * 1.8, dy * 1.8) * 12
        outline.append((cx + dx * reach, cy + dy * reach))
    return _chaikin(outline, 2)


def _chaikin(points: list[tuple[float, float]], iterations: int) -> list[tuple[float, float]]:
    current = list(points)
    for _ in range(iterations):
        nxt: list[tuple[float, float]] = []
        count = len(current)
        for index in range(count):
            x1, y1 = current[index]
            x2, y2 = current[(index + 1) % count]
            nxt.append((0.75 * x1 + 0.25 * x2, 0.75 * y1 + 0.25 * y2))
            nxt.append((0.25 * x1 + 0.75 * x2, 0.25 * y1 + 0.75 * y2))
        current = nxt
    return current


def _displace(points: list[tuple[float, float]], amount: float) -> list[tuple[float, float]]:
    cx = sum(x for x, _ in points) / len(points)
    cy = sum(y for _, y in points) / len(points)
    moved = []
    for x, y in points:
        dx, dy = x - cx, y - cy
        length = math.hypot(dx, dy) or 1.0
        shift = opensimplex.noise2(x * 0.0032, y * 0.0032) * amount
        moved.append((x + dx / length * shift, y + dy / length * shift))
    return moved


def _area(points: list[tuple[float, float]]) -> float:
    total = 0.0
    count = len(points)
    for index in range(count):
        x1, y1 = points[index]
        x2, y2 = points[(index + 1) % count]
        total += x1 * y2 - x2 * y1
    return abs(total) * 0.5


def _point_in_poly(x: float, y: float, points: list[tuple[float, float]]) -> bool:
    inside = False
    count = len(points)
    j = count - 1
    for i in range(count):
        xi, yi = points[i]
        xj, yj = points[j]
        if (yi > y) != (yj > y):
            denom = (yj - yi) or 1e-9
            if x < (xj - xi) * (y - yi) / denom + xi:
                inside = not inside
        j = i
    return inside

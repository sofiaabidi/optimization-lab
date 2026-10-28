from __future__ import annotations

from collections.abc import Sequence
from html import escape
from pathlib import Path


def write_bar_svg(labels: Sequence[str], values: Sequence[float], path: Path, title: str) -> Path:
    """Write a dependency-free SVG suitable for small result summaries."""
    if not labels or len(labels) != len(values):
        raise ValueError("labels and values must be non-empty and have equal length")
    if any(value < 0 for value in values):
        raise ValueError("bar values must be non-negative")
    maximum = max(values) or 1.0
    width, height, margin = 640, 360, 50
    plot_height = height - 2 * margin
    bar_width = (width - 2 * margin) / len(values)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="25" text-anchor="middle">{escape(title)}</text>',
    ]
    for index, (label, value) in enumerate(zip(labels, values, strict=True)):
        bar_height = plot_height * value / maximum
        x = margin + index * bar_width + 5
        y = height - margin - bar_height
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width - 10:.1f}" height="{bar_height:.1f}" fill="#4472c4"/>')
        parts.append(f'<text x="{x + (bar_width - 10) / 2:.1f}" y="{height - 30}" text-anchor="middle">{escape(label)}</text>')
    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return path

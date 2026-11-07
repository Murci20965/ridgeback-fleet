"""Builds the solution design as a draw.io source file and an SVG from one definition,
so the editable source and the exported image can't drift apart.

    python docs/diagram/build_diagram.py

Writes docs/solution_design.drawio and docs/diagram/solution_design.svg. The canvas is 16:9, so
the diagram fills a widescreen display. Titles sit above their panels and cards, and connectors
are routed so that none crosses another line, a card or a title.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 1600, 900
TITLE = "Ridgeback fleet data: production solution design"

INK = "#1d1d1f"
INK_2 = "#515154"
LINE = "#6e6e73"
LANE_FILL = "#f5f5f7"
PAGE_TITLE_SIZE = 26
LANE_TITLE_SIZE = 20
TITLE_SIZE = 19
BODY_SIZE = 16
LABEL_SIZE = 13
LINE_HEIGHT = 20
BODY_INSET = 14

# Fill, stroke, title colour, body colour. One blue marks the LLM, and red marks what goes wrong.
STYLES = {
    "plain": ("#ffffff", "#d2d2d7", INK, INK_2),
    "store": ("#e8e8ed", "#c7c7cc", INK, INK_2),
    "llm": ("#e8f2fd", "#0071e3", "#0058b0", INK_2),
    "fail": ("#ffffff", "#d70015", "#b00012", INK_2),
    "secret": (INK, INK, INK, "#f5f5f7"),
}

# title, x, y, width, height
LANES = [
    ("Ingest: runs unattended every morning", 20, 72, 1560, 126),
    ("Store", 20, 232, 1560, 106),
    ("Serve: dashboard and chat", 20, 372, 1560, 296),
    ("When files are late, missing or corrupt", 20, 700, 1560, 186),
]

# id, style, x, y, width, height, title, lines
NODES = [
    ("provider", "plain", 40, 108, 230, 80, "Telematics provider", ["Sends yesterday's events", "as a CSV at 04:00"]),
    ("sftp", "plain", 300, 108, 230, 80, "SFTP folder", ["Client's folder", "Stands in for data/incoming", "in this build"]),
    ("runner", "plain", 560, 108, 310, 80, "Scheduled runner", ["GitHub Actions cron, 04:00 SAST", "Retries hourly until 07:00", "Option: n8n Schedule trigger"]),
    ("pipeline", "plain", 900, 108, 310, 80, "Python pipeline", ["Cleans rows, oldest file first", "One transaction per file", "Safe to rerun: unique event keys"]),
    ("alert", "fail", 1240, 108, 320, 80, "Alerts", ["Email or Slack webhook", "On failed, partial or missing files"]),
    ("archive", "store", 40, 268, 360, 60, "Object storage (production)", ["Raw files kept as delivered", "Bad files moved to quarantine"]),
    ("db", "store", 430, 268, 640, 60, "Neon Postgres", ["telemetry_events, machines, drivers, branches", "Views: v_machine_daily_hours, v_driver_events, v_branch_daily"]),
    ("log", "store", 1100, 268, 460, 60, "Run log", ["Postgres ingest_runs: file, rows loaded, rejected, outcome", "Postgres rejected_rows: raw row and the reason"]),
    ("browser", "plain", 40, 408, 200, 196, "Operations manager", ["Browser on phone,", "tablet or desktop"]),
    ("web", "plain", 290, 408, 260, 80, "Next.js on Vercel", ["Dashboard and chat UI", "No secrets, no database"]),
    ("dashapi", "plain", 600, 408, 300, 80, "FastAPI: /api/v1/dashboard", ["Runs shared SQL queries", "On each page view, cached 60s"]),
    ("llm", "llm", 950, 408, 280, 80, "OpenRouter (LLM call)", ["Claude Haiku 5.5, then fallback", "Called only from FastAPI", "Spend cap on the key"]),
    ("chatapi", "plain", 290, 524, 260, 80, "FastAPI: /api/v1/chat", ["Rate limit, length limit", "Tool loop, 5 rounds at most", "Runs when a question is sent"]),
    ("tools", "store", 600, 524, 300, 80, "Typed read-only tools", ["Run hours, events, fleet, coverage", "Validated, parameterised SQL", "No free-form SQL"]),
    ("guard", "plain", 950, 524, 280, 80, "Answer guard", ["Figure not in a tool result:", "one retry, then withheld"]),
    ("secrets", "secret", 1270, 408, 290, 244, "Where secrets live", ["Vercel env vars:", "OPENROUTER_API_KEY", "DATABASE_URL (read-only role)", "", "GitHub Actions secret:", "DATABASE_URL (owner role)", "", "Never in the repo or browser"]),
    ("late", "fail", 40, 736, 365, 140, "Late data", ["A row keeps its event date, wherever", "it arrives, up to 7 days old", "Resent rows hit the unique key,", "so they load once", "A late file loads on the next retry", "Older rows are rejected with a reason"]),
    ("missing", "fail", 425, 736, 365, 140, "Missing file", ["No file by 07:00: alert the", "on-call contact", "A gap between delivery dates is logged", "Dashboard shows the last loaded date", "Chat states which dates it covers", "Backfills load in date order"]),
    ("corrupt", "fail", 810, 736, 365, 140, "Corrupt file", ["Empty, not UTF-8 or missing a column:", "roll back only that file, log failed", "Later files still load", "The run exits non-zero and alerts", "The file is quarantined, and a", "corrected copy reloads automatically"]),
    ("badrow", "fail", 1195, 736, 365, 140, "Bad rows in a good file", ["Stored in rejected_rows with a reason", "Good rows still load", "Truncated file: outcome is partial,", "flagged on the dashboard", "Unknown machine: held until it's on", "the list, then reprocessed"]),
]

NODE_BY_ID = {node[0]: node for node in NODES}

# Connectors that join facing edges in a straight line.
STRAIGHT = [
    ("provider", "sftp"),
    ("sftp", "runner"),
    ("runner", "pipeline"),
    ("pipeline", "alert"),
    ("web", "dashapi"),
    ("chatapi", "tools"),
    ("llm", "guard"),
]

# Connectors placed by hand, to stay clear of titles and other lines.
# source, target, points from start to end, dashed
ROUTED = [
    ("sftp", "archive", [(350, 188), (350, 268)], False),
    ("pipeline", "db", [(985, 188), (985, 268)], False),
    ("pipeline", "log", [(1190, 188), (1190, 268)], False),
    ("browser", "web", [(240, 448), (290, 448)], False),
    ("browser", "chatapi", [(240, 545), (290, 545)], False),
    ("chatapi", "browser", [(290, 585), (240, 585)], False),
    ("dashapi", "db", [(880, 408), (880, 328)], False),
    ("tools", "db", [(900, 564), (925, 564), (925, 328)], True),
    ("chatapi", "llm", [(370, 604), (370, 644), (1250, 644), (1250, 448), (1230, 448)], False),
    ("guard", "chatapi", [(1090, 604), (1090, 620), (470, 620), (470, 604)], False),
]

# x, baseline y, text
LABELS = [
    (410, 224, "copy of raw file"),
    (1030, 224, "loads events"),
    (1235, 224, "logs each run"),
    (902, 360, "SQL"),
    (975, 360, "read-only SQL"),
    (265, 442, "opens"),
    (265, 539, "asks"),
    (265, 579, "answer"),
    (575, 442, "fetch"),
    (575, 558, "tool"),
    (1140, 510, "draft answer"),
    (780, 636, "checked answer, or a clear 'the data can't answer'"),
    (810, 660, "asks model, sending the tool results"),
]


def facing_points(source: tuple, target: tuple) -> list[tuple[float, float]]:
    """Connect the facing edges of two boxes, in whichever direction separates them more."""
    _, _, sx, sy, sw, sh, *_ = source
    _, _, tx, ty, tw, th, *_ = target
    scy, tcy = sy + sh / 2, ty + th / 2
    if tx >= sx + sw:
        return [(sx + sw, scy), (tx, tcy)]
    if tx + tw <= sx:
        return [(sx, scy), (tx + tw, tcy)]
    x = (max(sx, tx) + min(sx + sw, tx + tw)) / 2
    if ty >= sy + sh:
        return [(x, sy + sh), (x, ty)]
    return [(x, sy), (x, ty + th)]


def all_connectors() -> list[tuple[str, str, list[tuple[float, float]], bool]]:
    straight = [
        (source, target, facing_points(NODE_BY_ID[source], NODE_BY_ID[target]), False)
        for source, target in STRAIGHT
    ]
    return straight + ROUTED


def build_svg() -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="Segoe UI, Arial, sans-serif">',
        f'<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto"><path d="M1 1L9 5L1 9z" fill="{LINE}"/></marker></defs>',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>',
        f'<text x="20" y="34" font-size="{PAGE_TITLE_SIZE}" font-weight="600" fill="{INK}">'
        f"{escape(TITLE)}</text>",
    ]
    for title, x, y, w, h in LANES:
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{LANE_FILL}"/>')
        parts.append(
            f'<text x="{x}" y="{y - 8}" font-size="{LANE_TITLE_SIZE}" font-weight="600" '
            f'fill="{INK}">{escape(title)}</text>'
        )
    for _, style, x, y, w, h, title, lines in NODES:
        fill, stroke, title_colour, body_colour = STYLES[style]
        parts.append(
            f'<text x="{x}" y="{y - 8}" font-size="{TITLE_SIZE}" font-weight="600" '
            f'fill="{title_colour}">{escape(title)}</text>'
        )
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1"/>'
        )
        top = y + (h - LINE_HEIGHT * len(lines)) / 2 + 15
        for index, line in enumerate(lines):
            parts.append(
                f'<text x="{x + BODY_INSET}" y="{top + LINE_HEIGHT * index}" '
                f'font-size="{BODY_SIZE}" fill="{body_colour}">{escape(line)}</text>'
            )
    for _, _, points, dashed in all_connectors():
        path = " ".join(f"{'M' if i == 0 else 'L'} {x} {y}" for i, (x, y) in enumerate(points))
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        parts.append(
            f'<path d="{path}" fill="none" stroke="{LINE}" stroke-width="1.5"{dash} '
            'marker-end="url(#a)"/>'
        )
    for x, y, text in LABELS:
        parts.append(
            f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{LABEL_SIZE}" fill="{INK_2}">'
            f"{escape(text)}</text>"
        )
    parts.append("</svg>")
    return "\n".join(parts)


def _text_cell(cell_id: str, text: str, x: float, y: float, w: float, h: float, style: str) -> str:
    return (
        f'<mxCell id="{cell_id}" value="{escape(text, quote=True)}" '
        f'style="text;html=1;whiteSpace=nowrap;strokeColor=none;fillColor=none;spacing=0;{style}" '
        f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" '
        'as="geometry"/></mxCell>'
    )


def _title_style(size: int, colour: str) -> str:
    return f"align=left;verticalAlign=middle;fontSize={size};fontStyle=1;fontColor={colour};"


def build_drawio() -> str:
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    cells.append(_text_cell("title", TITLE, 20, 10, 900, 32, _title_style(PAGE_TITLE_SIZE, INK)))
    for index, (title, x, y, w, h) in enumerate(LANES):
        style = f"rounded=1;arcSize=4;whiteSpace=wrap;html=1;fillColor={LANE_FILL};strokeColor=none;"
        cells.append(
            f'<mxCell id="lane{index}" value="" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        cells.append(
            _text_cell(f"lanetitle{index}", title, x, y - 30, w, 26, _title_style(LANE_TITLE_SIZE, INK))
        )
    for node_id, node_style, x, y, w, h, title, lines in NODES:
        fill, stroke, title_colour, body_colour = STYLES[node_style]
        cells.append(
            _text_cell(f"{node_id}title", title, x, y - 28, w, 26, _title_style(TITLE_SIZE, title_colour))
        )
        text = "<br>".join(escape(line) for line in lines)
        style = (
            f"rounded=1;arcSize=10;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
            f"fontSize={BODY_SIZE};fontColor={body_colour};align=left;verticalAlign=middle;"
            f"spacingLeft={BODY_INSET - 2};"
        )
        cells.append(
            f'<mxCell id="{node_id}" value="{escape(text, quote=True)}" style="{style}" '
            f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" '
            'as="geometry"/></mxCell>'
        )
    for index, (source, target, points, dashed) in enumerate(all_connectors()):
        _, _, sx, sy, sw, sh, *_ = NODE_BY_ID[source]
        _, _, tx, ty, tw, th, *_ = NODE_BY_ID[target]
        start, end = points[0], points[-1]
        style = (
            f"edgeStyle=none;rounded=0;html=1;endArrow=block;endFill=1;strokeColor={LINE};"
            f"strokeWidth=1.5;exitX={(start[0] - sx) / sw:.4f};exitY={(start[1] - sy) / sh:.4f};"
            f"exitDx=0;exitDy=0;entryX={(end[0] - tx) / tw:.4f};entryY={(end[1] - ty) / th:.4f};"
            f"entryDx=0;entryDy=0;{'dashed=1;' if dashed else ''}"
        )
        middle = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points[1:-1])
        waypoints = f'<Array as="points">{middle}</Array>' if middle else ""
        cells.append(
            f'<mxCell id="edge{index}" value="" style="{style}" edge="1" parent="1" '
            f'source="{source}" target="{target}"><mxGeometry relative="1" as="geometry">'
            f"{waypoints}</mxGeometry></mxCell>"
        )
    for index, (x, y, text) in enumerate(LABELS):
        width = 8 * len(text)
        cells.append(
            _text_cell(
                f"label{index}", text, x - width / 2, y - 14, width, 18,
                f"align=center;verticalAlign=middle;fontSize={LABEL_SIZE};fontColor={INK_2};",
            )
        )
    body = "".join(cells)
    return (
        '<mxfile host="app.diagrams.net"><diagram name="Solution design">'
        f'<mxGraphModel dx="{WIDTH}" dy="{HEIGHT}" grid="0" gridSize="10" page="1" '
        f'pageWidth="{WIDTH}" pageHeight="{HEIGHT}" background="#ffffff"><root>{body}</root>'
        "</mxGraphModel></diagram></mxfile>\n"
    )


if __name__ == "__main__":
    (DOCS / "solution_design.drawio").write_text(build_drawio(), encoding="utf-8", newline="\n")
    (DOCS / "diagram" / "solution_design.svg").write_text(build_svg(), encoding="utf-8", newline="\n")

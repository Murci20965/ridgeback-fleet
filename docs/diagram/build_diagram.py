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
WIDTH, HEIGHT = 1920, 1080
TITLE = "Ridgeback fleet data: production solution design"

INK = "#1d1d1f"
INK_2 = "#3a3a3c"
LINE = "#48484a"
LANE_FILL = "#eeeef2"
CARD_STROKE = "#86868b"
STROKE_WIDTH = 2
PAGE_TITLE_SIZE = 32
LANE_TITLE_SIZE = 25
TITLE_SIZE = 23
BODY_SIZE = 19
LABEL_SIZE = 16
LINE_HEIGHT = 25
BODY_INSET = 20

# Fill, stroke, title colour, body colour. Among the cards, blue marks the LLM and red marks what
# goes wrong.
STYLES = {
    "plain": ("#ffffff", CARD_STROKE, INK, INK_2),
    "store": ("#dcdce2", CARD_STROKE, INK, INK),
    "llm": ("#dcebfc", "#0071e3", "#0058b0", INK),
    "fail": ("#ffffff", "#d70015", "#b00012", INK_2),
    "secret": (INK, INK, INK, "#ffffff"),
}

LANE_BLUE = "#0071e3"

# title, x, y, width, height, border colour
LANES = [
    ("Ingest: runs unattended every morning", 20, 98, 1880, 172, LANE_BLUE),
    ("Store", 20, 318, 1880, 142, LANE_BLUE),
    ("Serve: dashboard and chat", 20, 508, 1880, 344, LANE_BLUE),
    ("When files are late, missing or corrupt", 20, 900, 1880, 168, None),
]

# id, style, x, y, width, height, title, lines
NODES = [
    ("provider", "plain", 40, 144, 320, 110, "Telematics provider", ["Sends yesterday's events", "as a CSV at 04:00"]),
    ("sftp", "plain", 420, 144, 320, 110, "SFTP folder", ["Client's folder", "Stands in for data/incoming", "in this build"]),
    ("runner", "plain", 800, 144, 320, 110, "Scheduled runner", ["GitHub Actions cron, 04:00 SAST", "Retries hourly until 07:00", "Option: n8n Schedule trigger"]),
    ("pipeline", "plain", 1180, 144, 320, 110, "Python pipeline", ["Cleans rows, oldest file first", "One transaction per file", "Safe to rerun: unique event keys"]),
    ("alert", "fail", 1560, 144, 320, 110, "Alerts", ["Email or Slack webhook", "Failed, partial or missing files"]),
    ("archive", "store", 40, 364, 460, 80, "Object storage (production)", ["Raw files kept as delivered", "Bad files moved to quarantine"]),
    ("db", "store", 540, 364, 780, 80, "Neon Postgres", ["telemetry_events, machines, drivers, branches", "Views: v_machine_daily_hours, v_driver_events, v_branch_daily"]),
    ("log", "store", 1360, 364, 520, 80, "Run log", ["Postgres ingest_runs: file, rows, outcome", "Postgres rejected_rows: raw row and reason"]),
    ("browser", "plain", 40, 554, 240, 206, "Operations manager", ["Browser on phone,", "tablet or desktop"]),
    ("web", "plain", 370, 554, 320, 80, "Next.js on Vercel", ["Dashboard and chat UI", "No secrets, no database"]),
    ("dashapi", "plain", 760, 554, 350, 80, "FastAPI: /api/v1/dashboard", ["Runs shared SQL queries", "On each page view, cached 60s"]),
    ("llm", "llm", 1190, 554, 320, 80, "OpenRouter (LLM call)", ["Claude Haiku 5.5, with fallback", "Called only from FastAPI"]),
    ("chatapi", "plain", 370, 680, 320, 80, "FastAPI: /api/v1/chat", ["Rate and length limits", "Tool loop, 5 rounds at most"]),
    ("tools", "store", 760, 680, 350, 80, "Typed read-only tools", ["Run hours, events, fleet, coverage", "Parameterised SQL, none free-form"]),
    ("guard", "plain", 1190, 680, 320, 80, "Answer guard", ["Figure not in a tool result:", "one retry, then withheld"]),
    ("secrets", "secret", 1580, 554, 300, 286, "Where secrets live", ["Vercel env vars:", "OPENROUTER_API_KEY", "DATABASE_URL (read-only)", "The key has a spend cap", "", "GitHub Actions secret:", "DATABASE_URL (owner)", "", "Never in the repo or browser"]),
    ("late", "fail", 40, 946, 437, 106, "Late data", ["Rows keep their event date, up to 7 days old", "Resent rows load once, by unique key", "A late file loads on the next retry"]),
    ("missing", "fail", 507, 946, 437, 106, "Missing file", ["No file by 07:00 alerts the on-call contact", "Gaps between delivery dates are logged", "Dashboard and chat show the dates covered"]),
    ("corrupt", "fail", 974, 946, 437, 106, "Corrupt file", ["Rolls back that file only, and logs it failed", "Later files still load, and the run alerts", "Quarantined until a corrected copy arrives"]),
    ("badrow", "fail", 1443, 946, 437, 106, "Bad rows in a good file", ["Stored in rejected_rows with a reason", "Good rows load; truncated means partial", "Unknown machines held until listed"]),
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
]

# Connectors placed by hand, to stay clear of titles and other lines.
# source, target, points from start to end, dashed
ROUTED = [
    ("sftp", "archive", [(460, 254), (460, 364)], False),
    ("pipeline", "db", [(1240, 254), (1240, 364)], False),
    ("pipeline", "log", [(1480, 254), (1480, 364)], False),
    ("browser", "web", [(280, 594), (370, 594)], False),
    ("browser", "chatapi", [(280, 700), (370, 700)], False),
    ("chatapi", "browser", [(370, 740), (280, 740)], False),
    ("dashapi", "db", [(1095, 554), (1095, 444)], False),
    ("tools", "db", [(1110, 720), (1150, 720), (1150, 444)], True),
    ("llm", "guard", [(1400, 634), (1400, 680)], False),
    ("chatapi", "llm", [(450, 760), (450, 818), (1545, 818), (1545, 594), (1510, 594)], False),
    ("guard", "chatapi", [(1350, 760), (1350, 782), (590, 782), (590, 760)], False),
]

# x, baseline y, text
LABELS = [
    (530, 300, "copy of raw file"),
    (1300, 300, "loads events"),
    (1545, 300, "logs each run"),
    (1122, 490, "SQL"),
    (1212, 490, "read-only SQL"),
    (325, 586, "opens"),
    (325, 692, "asks"),
    (325, 732, "answer"),
    (725, 586, "fetch"),
    (725, 712, "tool"),
    (1465, 662, "draft answer"),
    (970, 803, "checked answer, or a clear 'the data can't answer'"),
    (1000, 839, "asks model, sending the tool results"),
]


def facing_points(source: tuple, target: tuple) -> list[tuple[float, float]]:
    """Connect the facing edges of two boxes, side by side at their vertical centres."""
    _, _, sx, sy, sw, sh, *_ = source
    _, _, tx, ty, _, th, *_ = target
    return [(sx + sw, sy + sh / 2), (tx, ty + th / 2)]


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
        f'<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5.5" '
        f'markerHeight="5.5" orient="auto"><path d="M1 1L9 5L1 9z" fill="{LINE}"/></marker></defs>',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>',
        f'<text x="20" y="44" font-size="{PAGE_TITLE_SIZE}" font-weight="600" fill="{INK}">'
        f"{escape(TITLE)}</text>",
    ]
    for title, x, y, w, h, border in LANES:
        outline = f' stroke="{border}" stroke-width="{STROKE_WIDTH}"' if border else ""
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{LANE_FILL}"{outline}/>'
        )
        parts.append(
            f'<text x="{x}" y="{y - 10}" font-size="{LANE_TITLE_SIZE}" font-weight="600" '
            f'fill="{INK}">{escape(title)}</text>'
        )
    for _, style, x, y, w, h, title, lines in NODES:
        fill, stroke, title_colour, body_colour = STYLES[style]
        parts.append(
            f'<text x="{x}" y="{y - 10}" font-size="{TITLE_SIZE}" font-weight="600" '
            f'fill="{title_colour}">{escape(title)}</text>'
        )
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{STROKE_WIDTH}"/>'
        )
        top = y + (h - LINE_HEIGHT * len(lines)) / 2 + 18
        for index, line in enumerate(lines):
            parts.append(
                f'<text x="{x + BODY_INSET}" y="{top + LINE_HEIGHT * index}" '
                f'font-size="{BODY_SIZE}" fill="{body_colour}">{escape(line)}</text>'
            )
    for _, _, points, dashed in all_connectors():
        path = " ".join(f"{'M' if i == 0 else 'L'} {x} {y}" for i, (x, y) in enumerate(points))
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        parts.append(
            f'<path d="{path}" fill="none" stroke="{LINE}" stroke-width="{STROKE_WIDTH}"{dash} '
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
    cells.append(_text_cell("title", TITLE, 20, 12, 1200, 42, _title_style(PAGE_TITLE_SIZE, INK)))
    for index, (title, x, y, w, h, border) in enumerate(LANES):
        outline = f"strokeColor={border};strokeWidth={STROKE_WIDTH};" if border else "strokeColor=none;"
        style = f"rounded=1;arcSize=4;whiteSpace=wrap;html=1;fillColor={LANE_FILL};{outline}"
        cells.append(
            f'<mxCell id="lane{index}" value="" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        cells.append(
            _text_cell(f"lanetitle{index}", title, x, y - 38, w, 32, _title_style(LANE_TITLE_SIZE, INK))
        )
    for node_id, node_style, x, y, w, h, title, lines in NODES:
        fill, stroke, title_colour, body_colour = STYLES[node_style]
        cells.append(
            _text_cell(f"{node_id}title", title, x, y - 36, w, 30, _title_style(TITLE_SIZE, title_colour))
        )
        text = "<br>".join(escape(line) for line in lines)
        style = (
            f"rounded=1;arcSize=10;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
            f"strokeWidth={STROKE_WIDTH};fontSize={BODY_SIZE};fontColor={body_colour};align=left;"
            f"verticalAlign=middle;spacingLeft={BODY_INSET - 2};"
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
            f"strokeWidth={STROKE_WIDTH};exitX={(start[0] - sx) / sw:.4f};"
            f"exitY={(start[1] - sy) / sh:.4f};exitDx=0;exitDy=0;"
            f"entryX={(end[0] - tx) / tw:.4f};entryY={(end[1] - ty) / th:.4f};"
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
        width = 10 * len(text)
        cells.append(
            _text_cell(
                f"label{index}", text, x - width / 2, y - 17, width, 22,
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

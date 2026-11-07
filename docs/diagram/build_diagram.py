"""Builds the solution design as a draw.io source file and an SVG from one definition,
so the editable source and the exported image can't drift apart.

    python docs/diagram/build_diagram.py

Writes docs/solution_design.drawio and docs/diagram/solution_design.svg.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 1500, 1120

# Fill, stroke
COLOURS = {
    "lane": ("#f6f6f3", "#c3c2b7"),
    "source": ("#f0efec", "#6f6d68"),
    "run": ("#e6f0fc", "#2a78d6"),
    "store": ("#e1f5ee", "#0f6e56"),
    "app": ("#fdeee8", "#c2501f"),
    "llm": ("#efedfb", "#6250d6"),
    "fail": ("#fcebeb", "#a32d2d"),
    "secret": ("#fff6dd", "#b97f00"),
}

LANES = [
    ("Ingest: runs unattended every morning", 30, 70, 1440, 215),
    ("Store", 30, 300, 1440, 165),
    ("Serve: dashboard and chat", 30, 480, 1440, 310),
    ("When files are late, missing or corrupt", 30, 805, 1440, 285),
]

# id, kind, x, y, width, height, title, lines
NODES = [
    ("provider", "source", 55, 125, 200, 120, "Telematics provider", ["Sends yesterday's events", "as a CSV at 04:00"]),
    ("sftp", "source", 305, 125, 200, 120, "SFTP folder", ["Client's folder", "Stands in for data/incoming", "in this build"]),
    ("runner", "run", 555, 125, 260, 120, "Scheduled runner", ["GitHub Actions cron, 04:00 SAST", "Retries hourly until 07:00", "Option: n8n Schedule trigger"]),
    ("pipeline", "run", 865, 125, 320, 120, "Python pipeline", ["Cleans rows, oldest file first", "One transaction per file", "Safe to rerun: unique event keys"]),
    ("alert", "fail", 1235, 125, 210, 120, "Alerts", ["Email or Slack webhook", "On failed, partial or", "missing files"]),
    ("archive", "store", 55, 345, 330, 95, "Object storage (production)", ["Raw files kept as delivered", "Bad files moved to quarantine"]),
    ("db", "store", 435, 345, 480, 95, "Neon Postgres", ["telemetry_events, machines, drivers, branches", "Views: v_machine_daily_hours, v_driver_events, v_branch_daily"]),
    ("log", "store", 965, 345, 480, 95, "Run log in Postgres", ["ingest_runs: file, rows loaded and rejected, outcome", "rejected_rows: raw row and the reason"]),
    ("browser", "source", 55, 560, 190, 115, "Operations manager", ["Browser on phone,", "tablet or desktop"]),
    ("web", "app", 300, 530, 240, 85, "Next.js on Vercel", ["Dashboard and chat UI", "No secrets, no database"]),
    ("dashapi", "app", 590, 530, 250, 85, "FastAPI: /api/v1/dashboard", ["Runs shared SQL queries", "On each page view, cached 60s"]),
    ("chatapi", "app", 300, 660, 240, 100, "FastAPI: /api/v1/chat", ["Rate limit, length limit", "Tool loop, 5 rounds at most", "Runs when a question is sent"]),
    ("tools", "store", 590, 660, 250, 100, "Typed read-only tools", ["Run hours, events, fleet, coverage", "Validated, parameterised SQL", "No free-form SQL"]),
    ("guard", "app", 890, 530, 250, 85, "Answer guard", ["Figure not in a tool result:", "one retry, then withheld"]),
    ("llm", "llm", 890, 660, 250, 100, "OpenRouter (LLM call)", ["Claude Haiku 5.5, then fallback", "Called only from FastAPI", "Spend cap on the key"]),
    ("secrets", "secret", 1190, 530, 255, 230, "Where secrets live", ["Vercel env vars:", "OPENROUTER_API_KEY", "DATABASE_URL (read-only role)", "", "GitHub Actions secret:", "DATABASE_URL (owner role)", "", "Never in the repo or browser"]),
    ("late", "fail", 55, 860, 330, 205, "Late data", ["A row keeps its event date, wherever", "it arrives, up to 7 days old", "Resent rows hit the unique key,", "so they load once", "A late file loads on the next retry", "Older rows are rejected with a reason"]),
    ("missing", "fail", 410, 860, 330, 205, "Missing file", ["No file by 07:00: alert the on-call", "contact", "A gap between delivery dates is logged", "Dashboard shows the last loaded date", "Chat states which dates it covers", "Backfills load in date order"]),
    ("corrupt", "fail", 765, 860, 330, 205, "Corrupt file", ["Empty, not UTF-8 or missing a column:", "roll back only that file, log failed", "Later files still load", "The run exits non-zero and alerts", "The file is quarantined, and a", "corrected copy reloads automatically"]),
    ("badrow", "fail", 1120, 860, 325, 205, "Bad rows in a good file", ["Stored in rejected_rows with a reason", "Good rows still load", "Truncated file: outcome is partial,", "flagged on the dashboard", "Unknown machine: held until it's on", "the list, then reprocessed"]),
]

# source, target, label, label x, label y
EDGES = [
    ("provider", "sftp", "04:00 drop", None, None),
    ("sftp", "runner", "reads new files", None, None),
    ("runner", "pipeline", "runs", None, None),
    ("pipeline", "alert", "on problems", None, None),
    ("pipeline", "db", "loads events", None, None),
    ("pipeline", "log", "logs each run", None, None),
    ("sftp", "archive", "copy of raw file", None, None),
    ("browser", "web", "opens page", None, None),
    ("browser", "chatapi", "asks question", None, None),
    ("web", "dashapi", "server fetch", None, None),
    ("chatapi", "tools", "tool call", None, None),
    ("llm", "guard", "draft answer", None, None),
]
ROUTED_EDGES = [("chatapi", "llm", "asks model"), ("guard", "browser", "checked answer")]

NODE_BY_ID = {node[0]: node for node in NODES}


def anchor(source: tuple, target: tuple) -> tuple[float, float, float, float]:
    """Connect the facing edges of two boxes, in whichever direction separates them more."""
    _, _, sx, sy, sw, sh, *_ = source
    _, _, tx, ty, tw, th, *_ = target
    scx, scy, tcx, tcy = sx + sw / 2, sy + sh / 2, tx + tw / 2, ty + th / 2
    if tx >= sx + sw:
        return sx + sw, scy, tx, tcy
    if tx + tw <= sx:
        return sx, scy, tx + tw, tcy
    if ty >= sy + sh:
        x = (max(sx, tx) + min(sx + sw, tx + tw)) / 2
        return x, sy + sh, x, ty
    x = (max(sx, tx) + min(sx + sw, tx + tw)) / 2
    return x, sy, x, ty + th


def build_svg() -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="Segoe UI, Arial, sans-serif">',
        '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto"><path d="M1 1L9 5L1 9z" fill="#52514e"/></marker></defs>',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>',
        '<text x="30" y="42" font-size="24" font-weight="600" fill="#0b0b0b">'
        "Ridgeback fleet data: production solution design</text>",
    ]
    for title, x, y, w, h in LANES:
        fill, stroke = COLOURS["lane"]
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" '
            f'stroke="{stroke}"/>'
        )
        parts.append(
            f'<text x="{x + 16}" y="{y + 26}" font-size="15" font-weight="600" fill="#52514e">'
            f"{escape(title)}</text>"
        )
    for node_id, kind, x, y, w, h, title, lines in NODES:
        fill, stroke = COLOURS[kind]
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1.5"/>'
        )
        total = 22 + 18 * len(lines)
        top = y + (h - total) / 2 + 15
        parts.append(
            f'<text x="{x + w / 2}" y="{top}" text-anchor="middle" font-size="15" '
            f'font-weight="600" fill="#0b0b0b">{escape(title)}</text>'
        )
        for index, line in enumerate(lines):
            parts.append(
                f'<text x="{x + w / 2}" y="{top + 22 + 18 * index}" text-anchor="middle" '
                f'font-size="13" fill="#3d3d3a">{escape(line)}</text>'
            )
    for source, target, label, _, _ in EDGES:
        x1, y1, x2, y2 = anchor(NODE_BY_ID[source], NODE_BY_ID[target])
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#52514e" '
            'stroke-width="1.5" marker-end="url(#a)"/>'
        )
    # Paths a straight connector would draw through another box.
    for path, dashed in (
        ("M 715 530 L 715 442", False),  # dashboard queries
        ("M 840 715 L 865 715 L 865 495 L 800 495 L 800 442", True),  # tool queries
        ("M 420 760 L 420 777 L 1015 777 L 1015 762", False),  # route asks the model
        ("M 1015 530 L 1015 521 L 150 521 L 150 558", False),  # checked answer to the user
    ):
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        parts.append(
            f'<path d="{path}" fill="none" stroke="#52514e" stroke-width="1.5"{dash} '
            'marker-end="url(#a)"/>'
        )
    labels = [
        (1130, 293, "logs each run"),
        (780, 293, "loads events"),
        (690, 480, "SQL"),
        (855, 470, "read-only SQL"),
        (272, 545, "opens"),
        (262, 712, "asks"),
        (565, 562, "fetch"),
        (565, 708, "tool"),
        (700, 773, "asks model, sending the tool results"),
        (1078, 640, "draft answer"),
        (520, 516, "checked answer, or a clear 'the data can't answer'"),
    ]
    for x, y, text in labels:
        if text:
            parts.append(
                f'<text x="{x}" y="{y}" text-anchor="middle" font-size="12" fill="#52514e">'
                f"{escape(text)}</text>"
            )
    parts.append("</svg>")
    return "\n".join(parts)


def build_drawio() -> str:
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    for index, (title, x, y, w, h) in enumerate(LANES):
        fill, stroke = COLOURS["lane"]
        style = (
            f"rounded=1;arcSize=2;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
            "verticalAlign=top;align=left;spacingLeft=12;fontStyle=1;fontSize=15;fontColor=#52514e;"
        )
        cells.append(
            f'<mxCell id="lane{index}" value="{escape(title, quote=True)}" style="{style}" '
            f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" '
            'as="geometry"/></mxCell>'
        )
    for node_id, kind, x, y, w, h, title, lines in NODES:
        fill, stroke = COLOURS[kind]
        text = f"<b>{escape(title)}</b><br>" + "<br>".join(escape(line) for line in lines)
        style = (
            f"rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
            "fontSize=13;fontColor=#0b0b0b;"
        )
        cells.append(
            f'<mxCell id="{node_id}" value="{escape(text, quote=True)}" style="{style}" '
            f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" '
            'as="geometry"/></mxCell>'
        )
    edges = [(s, t, label) for s, t, label, _, _ in EDGES] + ROUTED_EDGES + [
        ("dashapi", "db", "SQL"),
        ("tools", "db", "read-only SQL"),
    ]
    for index, (source, target, label) in enumerate(edges):
        style = "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor=#52514e;fontSize=12;"
        cells.append(
            f'<mxCell id="edge{index}" value="{escape(label, quote=True)}" style="{style}" '
            f'edge="1" parent="1" source="{source}" target="{target}">'
            '<mxGeometry relative="1" as="geometry"/></mxCell>'
        )
    body = "".join(cells)
    return (
        '<mxfile host="app.diagrams.net"><diagram name="Solution design">'
        f'<mxGraphModel dx="{WIDTH}" dy="{HEIGHT}" grid="1" gridSize="10" page="1" '
        f'pageWidth="{WIDTH}" pageHeight="{HEIGHT}"><root>{body}</root></mxGraphModel>'
        "</diagram></mxfile>\n"
    )


if __name__ == "__main__":
    (DOCS / "solution_design.drawio").write_text(build_drawio(), encoding="utf-8")
    (DOCS / "diagram" / "solution_design.svg").write_text(build_svg(), encoding="utf-8")

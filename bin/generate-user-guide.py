from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# This script generates a fictional PDF manual used as local RAG test data.
# It intentionally includes specific invented terms and error codes so answers
# can be checked against the document rather than the base model's training.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "aster-pump-aftercare-backend" / "docs"
ASSETS_DIR = DOCS_DIR / "assets"
COVER_IMAGE = ASSETS_DIR / "asterpump_x17_cover.png"
OUTPUT_PDF = DOCS_DIR / "asterpump_x17_user_guide.pdf"


def build_styles() -> dict[str, ParagraphStyle]:
    """Create the small style set used by the generated guide."""

    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "GuideTitle",
            parent=base["Title"],
            fontSize=30,
            leading=36,
            textColor=colors.HexColor("#12343b"),
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "GuideSubtitle",
            parent=base["Normal"],
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#31525b"),
            spaceAfter=18,
        ),
        "heading": ParagraphStyle(
            "GuideHeading",
            parent=base["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f4c5c"),
            spaceBefore=12,
            spaceAfter=8,
        ),
        "subheading": ParagraphStyle(
            "GuideSubheading",
            parent=base["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#1c6b78"),
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "GuideBody",
            parent=base["BodyText"],
            fontSize=10.5,
            leading=15,
            spaceAfter=7,
        ),
        "note": ParagraphStyle(
            "GuideNote",
            parent=base["BodyText"],
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#4f5d75"),
            backColor=colors.HexColor("#eef7f8"),
            borderColor=colors.HexColor("#9ad1d4"),
            borderWidth=0.5,
            borderPadding=7,
            spaceBefore=8,
            spaceAfter=10,
        ),
    }


def bullet_items(styles: dict[str, ParagraphStyle], items: list[str]) -> ListFlowable:
    """Convert plain strings into a compact bullet list for the PDF."""

    return ListFlowable(
        [ListItem(Paragraph(item, styles["body"])) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=16,
    )


def add_page_number(canvas, doc) -> None:
    """Draw a subtle footer on every page except the first cover page."""

    if doc.page == 1:
        return
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Aster Pump X17 User Guide | Page {doc.page}")
    canvas.restoreState()


def build_story() -> list:
    """Build all PDF content in a sequence that ReportLab can render."""

    styles = build_styles()
    story: list = []

    story.append(Paragraph("Aster Pump X17", styles["title"]))
    story.append(Paragraph("User Guide and Troubleshooting Manual", styles["subtitle"]))

    if COVER_IMAGE.exists():
        # The image is included at a large size so the E-77 display remains
        # readable when the PDF page is used as image-analysis test input.
        story.append(Image(str(COVER_IMAGE), width=14.5 * cm, height=20 * cm, kind="proportional"))

    story.append(Spacer(1, 0.4 * cm))
    story.append(PageBreak())

    story.append(Paragraph("1. Product Overview", styles["heading"]))
    story.append(
        Paragraph(
            "The Aster Pump X17 is a fictional smart cooling pump used for this local aftercare and RAG proof of concept. "
            "The unit supports three operating modes: Bluefin, Orchard, and Nightglass.",
            styles["body"],
        )
    )
    story.append(
        bullet_items(
            styles,
            [
                "Bluefin mode is used for normal daytime cooling.",
                "Orchard mode is used only when humidity is above 72 percent.",
                "Nightglass mode is used for quiet overnight operation.",
            ],
        )
    )

    story.append(Paragraph("2. Operating Modes", styles["heading"]))
    mode_table = Table(
        [
            ["Mode", "Dial Position", "When to Use", "Important Restriction"],
            ["Bluefin", "4", "Normal daytime cooling", "Default mode for stable operation."],
            ["Orchard", "6", "Humidity above 72 percent", "Do not use below 72 percent humidity."],
            ["Nightglass", "2", "Silent overnight operation", "Do not use during pressure echo recovery."],
        ],
        colWidths=[3.0 * cm, 3.0 * cm, 5.0 * cm, 6.0 * cm],
    )
    mode_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f4c5c")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9ca3af")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f7f8")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(mode_table)

    story.append(Paragraph("3. Error Codes", styles["heading"]))
    story.append(Paragraph("E-41: Silver Impeller Sensor Misalignment", styles["subheading"]))
    story.append(
        Paragraph(
            "Power down the unit, reseat the silver impeller sensor, and run calibration cycle C2 before returning the unit to service.",
            styles["body"],
        )
    )
    story.append(Paragraph("E-77: Coolant Loop Pressure Echo", styles["subheading"]))
    story.append(
        Paragraph(
            "Error code E-77 means the coolant loop has detected a pressure echo. Inspect the return valve, drain 200 ml of coolant, "
            "and restart the pressure monitor.",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            "If E-77 appears twice within one hour, do not restart the unit. Escalate to a Level 2 technician and leave the pressure monitor offline.",
            styles["note"],
        )
    )
    story.append(Paragraph("E-93: Filter Cassette Expired", styles["subheading"]))
    story.append(
        Paragraph(
            "Replace the filter cassette and confirm the cassette date stamp in the service panel before restarting normal operation.",
            styles["body"],
        )
    )

    story.append(Paragraph("4. Maintenance Schedule", styles["heading"]))
    story.append(
        bullet_items(
            styles,
            [
                "Replace the filter cassette every 19 days, not monthly.",
                "Write the replacement date on the green service tag.",
                "Inspect the coolant loop every 11 days.",
                "Run calibration cycle C2 after sensor replacement, moving the unit more than 5 meters, or firmware updates.",
                "Only Level 2 technicians may approve operation after repeated E-77 pressure echo events.",
            ],
        )
    )

    return story


def main() -> None:
    """Generate the PDF guide in the backend docs directory."""

    if not COVER_IMAGE.exists():
        raise FileNotFoundError(f"Missing cover image: {COVER_IMAGE}")

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title="Aster Pump X17 User Guide",
        author="Aster Pump Aftercare PoC",
    )
    doc.build(build_story(), onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"Generated {OUTPUT_PDF}")


if __name__ == "__main__":
    main()

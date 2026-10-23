from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "optimind-ubuntu-docker-setup.pdf"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#11263D")
BLUE = colors.HexColor("#2563EB")
PALE_BLUE = colors.HexColor("#EAF2FF")
INK = colors.HexColor("#1F2937")
MUTED = colors.HexColor("#64748B")
CODE_BG = colors.HexColor("#F1F5F9")
GREEN = colors.HexColor("#0F766E")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold",
    fontSize=30, leading=35, textColor=NAVY, alignment=TA_CENTER, spaceAfter=10,
))
styles.add(ParagraphStyle(
    name="CoverSubtitle", parent=styles["Normal"], fontName="Helvetica",
    fontSize=13, leading=19, textColor=MUTED, alignment=TA_CENTER,
))
styles.add(ParagraphStyle(
    name="H1Custom", parent=styles["Heading1"], fontName="Helvetica-Bold",
    fontSize=20, leading=25, textColor=NAVY, spaceBefore=7, spaceAfter=10,
))
styles.add(ParagraphStyle(
    name="H2Custom", parent=styles["Heading2"], fontName="Helvetica-Bold",
    fontSize=13, leading=17, textColor=BLUE, spaceBefore=9, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="BodyCustom", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=9.5, leading=14, textColor=INK, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="Small", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8, leading=11, textColor=MUTED,
))
styles.add(ParagraphStyle(
    name="BulletCustom", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=9.5, leading=14, leftIndent=13, firstLineIndent=-8,
    bulletIndent=2, textColor=INK, spaceAfter=3,
))
styles.add(ParagraphStyle(
    name="CodeCustom", parent=styles["Code"], fontName="Courier",
    fontSize=7.8, leading=11, textColor=INK, leftIndent=8, rightIndent=8,
    borderPadding=8,
))
styles.add(ParagraphStyle(
    name="Callout", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=9.2, leading=13, textColor=GREEN, leftIndent=7,
))


def p(text: str, style: str = "BodyCustom") -> Paragraph:
    return Paragraph(text, styles[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(f"• {text}", styles["BulletCustom"])


def code(text: str) -> Table:
    block = Preformatted(text.strip("\n"), styles["CodeCustom"])
    table = Table([[block]], colWidths=[170 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def callout(text: str) -> Table:
    table = Table([[p(text, "Callout")]], colWidths=[170 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def footer(canvas, doc):
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(colors.HexColor("#D7DEE8"))
    canvas.setLineWidth(0.4)
    canvas.line(20 * mm, 14 * mm, width - 20 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 9 * mm, "OptiMind • Ubuntu Docker Setup")
    canvas.drawRightString(width - 20 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


story = []

# Cover
story += [Spacer(1, 43 * mm), p("OPTIMIND", "Small"), Spacer(1, 6 * mm)]
story += [p("Ubuntu + Docker Setup", "CoverTitle")]
story += [p("A practical guide to running the local-first AI workspace on an Ubuntu server.", "CoverSubtitle")]
story += [Spacer(1, 15 * mm), HRFlowable(width="55%", thickness=2, color=BLUE, hAlign="CENTER")]
story += [Spacer(1, 12 * mm), p("Includes PostgreSQL, Ollama, SearXNG, FastAPI, and the React frontend.", "CoverSubtitle")]
story += [Spacer(1, 55 * mm), p("October 2026 • Internal deployment guide", "Small"), PageBreak()]

story += [p("1. What this setup runs", "H1Custom")]
story += [p("The Docker Compose profile starts the core OptiMind stack as separate containers:")]
for item in [
    "React/Vite frontend on port 5173",
    "FastAPI backend on port 8000",
    "PostgreSQL with persistent database storage",
    "Ollama with a persistent model volume",
    "SearXNG for free local web search",
]:
    story.append(bullet(item))
story += [Spacer(1, 4), callout("Database migrations run automatically when the backend container starts. The first run downloads the configured Ollama model and may take several minutes."), Spacer(1, 8)]
story += [p("Image generation is disabled by default because its CPU/GPU runtime is hardware-specific. It can be added separately after the core stack is working.")]

story += [p("2. Ubuntu prerequisites", "H1Custom")]
story += [p("Install Ubuntu updates, Git, Docker Engine, and the Docker Compose plugin. Confirm the installation:")]
story += [code("docker --version\ndocker compose version\ngit --version")]
story += [Spacer(1, 6), p("If Docker requires sudo, either prefix Docker commands with sudo or add your user to the Docker group and sign in again:")]
story += [code('sudo usermod -aG docker "$USER"')]

story += [p("3. Download and configure", "H1Custom")]
story += [code("git clone <your-repository-url> optimind\ncd optimind\ncp .env.docker.example .env\nchmod 600 .env")]
story += [p("Edit .env and set a strong database password and search secret. Choose the model that fits the server:")]
model_data = [[p("Server memory", "Small"), p("Suggested model", "Small"), p("Trade-off", "Small")],
              [p("8 GB", "Small"), p("qwen2.5:1.5b", "Small"), p("Fastest and lightest", "Small")],
              [p("16 GB+", "Small"), p("qwen2.5:3b", "Small"), p("Better quality", "Small")]]
model_table = Table(model_data, colWidths=[45 * mm, 55 * mm, 70 * mm])
model_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
    ("BACKGROUND", (0, 1), (-1, -1), colors.white), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story += [model_table, Spacer(1, 7), code("OLLAMA_MODEL=qwen2.5:1.5b")]

story += [KeepTogether([
    p("4. Start the project", "H1Custom"),
    code("docker compose up -d --build\ndocker compose ps"),
    p("Open the app on the Ubuntu machine:"),
    code("http://localhost:5173"),
])]
story += [p("Follow startup logs or check all dependencies:")]
story += [code("docker compose logs -f backend\ncurl http://localhost:8000/api/v1/status")]

story += [p("5. Automatic startup after reboot", "H1Custom")]
story += [p("The services use restart: unless-stopped. Enable Docker at boot and start the stack once:")]
story += [code("sudo systemctl enable --now docker\ndocker compose up -d")]
story += [p("After Ubuntu reboots, Docker automatically brings the containers back. Verify with:")]
story += [code("docker compose ps")]
story += [PageBreak()]

story += [p("6. Access from another office computer", "H1Custom")]
story += [p("The frontend is published on all host interfaces. Find the Ubuntu server's static/private IP:")]
story += [code("hostname -I")]
story += [p("If the address is 192.168.1.50, open this from another computer on the same office network:")]
story += [code("http://192.168.1.50:5173")]
story += [p("If UFW is enabled, allow only the private office subnet:")]
story += [code("sudo ufw allow from 192.168.1.0/24 to any port 5173 proto tcp\nsudo ufw status")]
story += [p("Replace 192.168.1.0/24 with the actual office network range.")]
story += [callout("Do not expose PostgreSQL, Ollama, SearXNG, or port 8000 to the public internet. Only expose the frontend, or place it behind a VPN/reverse proxy.")]

story += [p("7. Use an office hostname", "H1Custom")]
story += [p("Yes. Create an internal DNS record in the office router, Pi-hole, or Windows/AD DNS:")]
story += [code("optimind.office.example  ->  192.168.1.50")]
story += [p("Then add the hostname to .env:")]
story += [code("VITE_ALLOWED_HOSTS=optimind.office.example")]
story += [p("Rebuild the frontend:")]
story += [code("docker compose up -d --build frontend")]
story += [p("Users can then open:")]
story += [code("http://optimind.office.example:5173")]
story += [p("For a quick office-only test without DNS, add this line to each client computer's hosts file:")]
story += [code("192.168.1.50  optimind.office")]
story += [p("Then browse to http://optimind.office:5173.")]

story += [p("8. Stop, update, and troubleshoot", "H1Custom")]
story += [code("docker compose down                    # stop without deleting data\ndocker compose up -d --build           # rebuild after code changes\ndocker compose logs -f                  # follow all logs\ndocker compose restart backend         # restart only the API")]
story += [p("To remove the database and Ollama model volumes as well (destructive):")]
story += [code("docker compose down -v")]
story += [p("If the page does not open, check the container state, listening port, firewall, and server address:")]
story += [code("docker compose ps\nss -ltnp | grep 5173\ncurl http://192.168.1.50:5173")]
story += [Spacer(1, 10), HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#CBD5E1")), Spacer(1, 6)]
story += [p("For a polished permanent deployment, put Nginx or Caddy in front of the frontend and use HTTPS. Do not expose the Vite development server directly to the public internet.", "Small")]

doc = SimpleDocTemplate(
    str(OUTPUT), pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm,
    topMargin=17 * mm, bottomMargin=20 * mm, title="OptiMind Ubuntu Docker Setup",
    author="OptiMind",
)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT)

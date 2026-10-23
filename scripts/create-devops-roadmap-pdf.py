from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
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
OUTPUT = ROOT / "output" / "pdf" / "docker-cicd-devops-roadmap.pdf"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#12263F")
BLUE = colors.HexColor("#2563EB")
TEAL = colors.HexColor("#0F766E")
PALE = colors.HexColor("#EEF5FF")
CODE_BG = colors.HexColor("#F1F5F9")
INK = colors.HexColor("#243447")
MUTED = colors.HexColor("#64748B")
GRID = colors.HexColor("#CBD5E1")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=29, leading=34, alignment=TA_CENTER, textColor=NAVY))
styles.add(ParagraphStyle(name="CoverSub", parent=styles["Normal"], fontName="Helvetica", fontSize=13, leading=18, alignment=TA_CENTER, textColor=MUTED))
styles.add(ParagraphStyle(name="H1R", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=NAVY, spaceBefore=5, spaceAfter=9))
styles.add(ParagraphStyle(name="H2R", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=BLUE, spaceBefore=8, spaceAfter=5))
styles.add(ParagraphStyle(name="BodyR", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.4, leading=13.5, textColor=INK, spaceAfter=5))
styles.add(ParagraphStyle(name="SmallR", parent=styles["BodyText"], fontName="Helvetica", fontSize=8, leading=11, textColor=MUTED))
styles.add(ParagraphStyle(name="BulletR", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2, leading=13, leftIndent=13, firstLineIndent=-8, textColor=INK, spaceAfter=2))
styles.add(ParagraphStyle(name="CodeR", parent=styles["Code"], fontName="Courier", fontSize=7.7, leading=10.5, textColor=INK, leftIndent=7, rightIndent=7, borderPadding=7))
styles.add(ParagraphStyle(name="CalloutR", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9, leading=12.5, textColor=TEAL, leftIndent=6))


def p(text, style="BodyR"):
    return Paragraph(text, styles[style])


def bullet(text):
    return Paragraph(f"• {text}", styles["BulletR"])


def code(text):
    table = Table([[Preformatted(text.strip(), styles["CodeR"])]], colWidths=[170 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG), ("BOX", (0, 0), (-1, -1), 0.45, GRID),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def callout(text):
    table = Table([[p(text, "CalloutR")]], colWidths=[170 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), 0.6, BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def footer(canvas, doc):
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(GRID)
    canvas.line(20 * mm, 14 * mm, width - 20 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 9 * mm, "Docker, CI/CD, and DevOps Roadmap")
    canvas.drawRightString(width - 20 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


story = [Spacer(1, 42 * mm), p("LEARN BY BUILDING", "SmallR"), Spacer(1, 5 * mm)]
story += [p("Docker, CI/CD & DevOps", "CoverTitle"), p("A practical 12-week roadmap from containers to reliable production delivery.", "CoverSub")]
story += [Spacer(1, 14 * mm), HRFlowable(width="55%", thickness=2, color=BLUE, hAlign="CENTER"), Spacer(1, 12 * mm)]
story += [p("Use the OptiMind project as your running laboratory: containerize it, test it, deploy it, monitor it, and improve it.", "CoverSub"), Spacer(1, 55 * mm), p("October 2026 • Practical learning plan", "SmallR"), PageBreak()]

story += [p("How to use this roadmap", "H1R"), p("Study the concept, complete the lab, and write down what you learned. Each week should end with something that runs and can be demonstrated.")]
for item in [
    "Spend 60-90 minutes learning and 60-90 minutes building on most days.",
    "Keep every lab in Git with a README, a diagram, and a rollback note.",
    "Prefer small, repeatable automation over manual server work.",
    "Do not move to the next stage until you can explain the current stage to someone else.",
]:
    story.append(bullet(item))
story += [Spacer(1, 5), callout("Target outcome: by the end, one commit can run tests, build an image, publish an artifact, deploy safely, and provide enough logs and health checks to diagnose failures."), Spacer(1, 8)]

story += [p("The learning path", "H1R")]
rows = [[p("Weeks", "SmallR"), p("Focus", "SmallR"), p("Deliverable", "SmallR")],
        [p("1-2", "SmallR"), p("Linux, Git, networking", "SmallR"), p("A documented Ubuntu lab server", "SmallR")],
        [p("3-4", "SmallR"), p("Docker fundamentals", "SmallR"), p("OptiMind running with Compose", "SmallR")],
        [p("5-6", "SmallR"), p("Images, registries, security", "SmallR"), p("Small, reproducible production images", "SmallR")],
        [p("7-8", "SmallR"), p("CI/CD pipelines", "SmallR"), p("Automated test, build, and deploy pipeline", "SmallR")],
        [p("9-10", "SmallR"), p("Infrastructure and observability", "SmallR"), p("Health checks, logs, metrics, alerts", "SmallR")],
        [p("11-12", "SmallR"), p("Reliability and capstone", "SmallR"), p("Documented zero-downtime release", "SmallR")]]
table = Table(rows, colWidths=[25 * mm, 62 * mm, 83 * mm])
table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("GRID", (0, 0), (-1, -1), 0.35, GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story += [table, PageBreak()]

story += [p("Phase 1 - Foundations (Weeks 1-2)", "H1R"), p("Learn enough Linux and networking to understand where an application is running and why a connection succeeds or fails.")]
story += [p("Study", "H2R")]
for item in ["Processes, services, systemd, users, groups, permissions, SSH, files, and logs.", "TCP/IP basics, ports, DNS, HTTP, localhost versus a network IP, and firewalls.", "Git branches, commits, pull requests, environment variables, and secrets."]:
    story.append(bullet(item))
story += [p("Lab", "H2R"), code("sudo systemctl status docker\nip addr\nss -ltnp\ncurl http://localhost:5173\ngit log --oneline -5")]
story += [p("Definition of done", "H2R"), bullet("You can explain the path from a browser request to a container and identify the port at each step.")]

story += [p("Phase 2 - Docker fundamentals (Weeks 3-4)", "H1R"), p("Understand images, containers, networks, volumes, Dockerfiles, and Compose.")]
story += [p("Study", "H2R")]
for item in ["Dockerfile instructions: FROM, WORKDIR, COPY, RUN, ENV, EXPOSE, and CMD.", "The difference between an image and a container; container lifecycle and logs.", "Compose services, depends_on, health checks, environment variables, and volumes."]:
    story.append(bullet(item))
story += [p("Lab", "H2R"), code("docker build -t optimind-backend -f backend/Dockerfile .\ndocker compose up -d --build\ndocker compose ps\ndocker compose logs -f backend\ndocker compose down")]
story += [p("Definition of done", "H2R"), bullet("You can rebuild OptiMind from a clean checkout and explain what data survives docker compose down.")]

story += [PageBreak(), p("Phase 3 - Images, registries, and security (Weeks 5-6)", "H1R"), p("Make images smaller, safer, and repeatable.")]
for item in ["Use .dockerignore, multi-stage builds, pinned versions, non-root users, and minimal base images.", "Understand image tags, digests, registries, vulnerability scanning, and secret handling.", "Separate build-time configuration from runtime configuration; never bake passwords into images."]:
    story.append(bullet(item))
story += [p("Lab", "H2R"), code("docker image ls\ndocker history optimind-backend\ndocker inspect optimind-backend\ndocker compose config --quiet")]
story += [callout("Security rule: environment files and secrets stay outside Git. A Docker image should be safe to share without exposing credentials.")]

story += [p("Phase 4 - CI/CD (Weeks 7-8)", "H1R"), p("CI/CD turns a code change into a tested, reviewable, repeatable release.")]
story += [p("Continuous Integration", "H2R")]
for item in ["Run linting, unit tests, type checks, and a frontend build on every pull request.", "Fail fast, keep logs readable, cache dependencies, and publish test results."]:
    story.append(bullet(item))
story += [p("Continuous Delivery", "H2R")]
for item in ["Build an immutable image after tests pass, tag it with the commit SHA, and publish it to a registry.", "Deploy to staging automatically; require an approval for production if the risk warrants it.", "Use health checks, a migration step, and a rollback procedure."]:
    story.append(bullet(item))
story += [p("Example pipeline stages", "H2R"), code("checkout -> install -> lint/test -> build -> scan -> publish -> deploy -> smoke test")]
story += [p("Lab", "H2R"), bullet("Create a CI workflow for OptiMind that runs the existing npm build and backend pytest suite, then builds both Docker images.")]
story += [p("Starter GitHub Actions pipeline", "H2R"), code("name: CI\non:\n  pull_request:\n  push:\n    branches: [main]\njobs:\n  test-build:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-node@v4\n        with: {node-version: 20, cache: npm}\n      - run: npm ci --prefix frontend\n      - run: npm run build --prefix frontend\n      - uses: actions/setup-python@v5\n        with: {python-version: '3.12'}\n      - run: pip install -r backend/requirements.txt\n      - run: pytest -q backend/tests")]
story += [p("Free places to run it", "H2R")]
free_rows = [[p("Option", "SmallR"), p("Best for", "SmallR"), p("Notes", "SmallR")],
             [p("GitHub Actions", "SmallR"), p("Public repos and learning", "SmallR"), p("Hosted runners; free usage is limited for private repositories", "SmallR")],
             [p("GitLab CI/CD", "SmallR"), p("A complete GitLab workflow", "SmallR"), p("Free shared runner minutes; bring your own runner for more control", "SmallR")],
             [p("Jenkins", "SmallR"), p("A fully self-hosted lab", "SmallR"), p("Free software; run it on your Ubuntu Docker server", "SmallR")],
             [p("Gitea or Woodpecker", "SmallR"), p("Private, self-hosted Git", "SmallR"), p("Free software; you provide the server and maintenance", "SmallR")]]
free_table = Table(free_rows, colWidths=[38 * mm, 48 * mm, 84 * mm])
free_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("GRID", (0, 0), (-1, -1), 0.35, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
story += [free_table, Spacer(1, 6), callout("Recommended starting setup: GitHub Actions for CI plus your Ubuntu Docker machine as the deployment target. It costs nothing for a small public project; private repositories have usage limits and the server still consumes electricity.")]

story += [p("Phase 5 - Infrastructure and observability (Weeks 9-10)", "H1R"), p("Learn how to operate the system after deployment.")]
for item in ["Infrastructure as code concepts: declared state, reviewable changes, drift, and repeatability.", "Logs: structured messages, correlation IDs, retention, and useful error context.", "Metrics: request rate, latency, error rate, container restarts, disk, memory, and model latency.", "Health checks, readiness versus liveness, alert thresholds, and incident notes."]:
    story.append(bullet(item))
story += [p("Lab", "H2R"), code("docker stats\ndocker compose ps\ncurl http://localhost:8000/api/v1/status\ndocker compose logs --since=10m")]

story += [PageBreak(), p("Phase 6 - Reliability and capstone (Weeks 11-12)", "H1R"), p("Bring the skills together in one production-style release process.")]
story += [p("Capstone project", "H2R"), p("Deploy OptiMind on an Ubuntu office server with a static IP or internal hostname. The finished system should have:")]
for item in ["Docker Compose with persistent PostgreSQL and Ollama volumes.", "Automatic startup after reboot and a documented backup/restore process.", "A CI pipeline that tests and builds every change.", "A staging or test environment, a smoke test, and a rollback command.", "A dashboard or at least a repeatable status and log-check procedure.", "An internal hostname with firewall rules that expose only the frontend."]:
    story.append(bullet(item))
story += [p("Release checklist", "H2R")]
check_rows = [[p("Check", "SmallR"), p("Evidence", "SmallR")],
              [p("Build", "SmallR"), p("Images build from a clean checkout", "SmallR")],
              [p("Test", "SmallR"), p("CI passes lint, tests, and frontend build", "SmallR")],
              [p("Deploy", "SmallR"), p("Compose starts and migrations complete", "SmallR")],
              [p("Health", "SmallR"), p("Status endpoint and smoke test pass", "SmallR")],
              [p("Rollback", "SmallR"), p("Previous image/tag can be restored", "SmallR")],
              [p("Security", "SmallR"), p("Secrets are not in Git or images", "SmallR")]]
check_table = Table(check_rows, colWidths=[42 * mm, 128 * mm])
check_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("GRID", (0, 0), (-1, -1), 0.35, GRID), ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
story += [check_table, Spacer(1, 8), callout("Your goal is not to memorize Docker commands. Your goal is to make delivery predictable: build, test, deploy, observe, recover.")]

story += [p("Recommended daily practice", "H1R")]
for item in ["Read one short concept and immediately run one command.", "Break something safely, then recover it using logs and documentation.", "Write a one-paragraph incident note for every failure: symptom, cause, fix, prevention.", "Keep a personal command reference, but always understand what each command changes."]:
    story.append(bullet(item))
story += [Spacer(1, 8), HRFlowable(width="100%", thickness=0.6, color=GRID), Spacer(1, 6), p("Once this roadmap is complete, the next specialization can be Kubernetes, Terraform, cloud networking, or platform engineering - choose based on the kind of systems you want to operate.", "SmallR")]

doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=17 * mm, bottomMargin=20 * mm, title="Docker, CI/CD, and DevOps Roadmap", author="OptiMind")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT)

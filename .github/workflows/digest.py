pythonimport anthropic
import json
import smtplib
import os
from email.mime.text import MIMEText
from datetime import date
from pathlib import Path

PROFILE = """
George Hambrecht, Associate Professor of Anthropology, University of Maryland.
Zooarchaeologist specializing in North Atlantic historical ecology.
Core areas:
- Marine historical ecology, Atlantic cod, Iceland (CAMHEP NSF project)
- Outer Hebrides archaeological survey, South Uist
- Shifting baseline syndrome in fisheries
- Climate change and cultural heritage
- North Atlantic human-environment interaction, millennial timescales
Relevant funders: NSF Arctic/Environmental/Archaeology, NEH,
Wenner-Gren Foundation, National Geographic Society,
AHRC, Historic Environment Scotland
"""

PROMPT = f"""
Today: {date.today()}

You are a research intelligence assistant. Use web search to find REAL,
CURRENT items published or announced in the last 30 days.

Search for:
RESEARCH: marine historical ecology 2025, zooarchaeology Iceland 2025,
Atlantic cod historical fisheries, Outer Hebrides archaeology 2025,
North Atlantic climate archaeology, shifting baseline syndrome fisheries

FUNDING: NSF Arctic Social Science deadline 2025, NEH fellowship 2025,
Wenner-Gren grant 2025, National Geographic Society grant 2025,
AHRC research grant 2025, Historic Environment Scotland funding 2025

Researcher profile:
{PROFILE}

Return ONLY valid JSON, no markdown fences, no preamble:
{{
  "week": "{date.today()}",
  "headline": "one sentence summarizing the most important find",
  "research": [
    {{
      "title": "title",
      "authors": "authors or source",
      "summary": "2-3 sentences on relevance to Georges work",
      "url": "url if available",
      "relevance": "high|medium|low",
      "type": "paper|preprint|news|report"
    }}
  ],
  "funding": [
    {{
      "funder": "funder name",
      "program": "program name",
      "amount": "amount",
      "deadline": "deadline date",
      "fit": "high|medium|low",
      "fit_reason": "one sentence",
      "url": "url"
    }}
  ]
}}
"""

def run_digest():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": PROMPT}]
    )
    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])

def format_email(data):
    lines = []
    lines.append(f"WEEKLY RESEARCH & FUNDING DIGEST — {data['week']}")
    lines.append("=" * 55)
    if data.get("headline"):
        lines.append(f"\n{data['headline']}\n")
    research = data.get("research", [])
    if research:
        lines.append(f"NEW RESEARCH ({len(research)} items)")
        lines.append("-" * 40)
        for i, r in enumerate(research, 1):
            lines.append(f"\n{i}. {r['title']}")
            if r.get("authors"):
                lines.append(f"   {r['authors']}")
            lines.append(f"   {r['summary']}")
            lines.append(f"   Fit: {r['relevance']} | Type: {r['type']}")
            if r.get("url", "").startswith("http"):
                lines.append(f"   {r['url']}")
    funding = data.get("funding", [])
    if funding:
        lines.append(f"\n\nFUNDING OPPORTUNITIES ({len(funding)} items)")
        lines.append("-" * 40)
        for i, f in enumerate(funding, 1):
            lines.append(f"\n{i}. {f['funder']} — {f['program']}")
            lines.append(f"   Deadline: {f['deadline']} | Amount: {f['amount']}")
            lines.append(f"   {f['fit_reason']}")
            lines.append(f"   Fit: {f['fit']}")
            if f.get("url", "").startswith("http"):
                lines.append(f"   {f['url']}")
    lines.append("\n" + "=" * 55)
    lines.append("Reply to this email to act on any item.")
    return "\n".join(lines)

def save_to_archive(data, body):
    archive_dir = Path("archive")
    archive_dir.mkdir(exist_ok=True)
    txt_path = archive_dir / f"{data['week']}.txt"
    txt_path.write_text(body)
    md_lines = []
    md_lines.append(f"# Research Digest — {data['week']}\n")
    if data.get("headline"):
        md_lines.append(f"> {data['headline']}\n")
    research = data.get("research", [])
    if research:
        md_lines.append(f"## New Research ({len(research)} items)\n")
        for r in research:
            md_lines.append(f"### {r['title']}")
            if r.get("authors"):
                md_lines.append(f"*{r['authors']}*\n")
            md_lines.append(f"{r['summary']}\n")
            md_lines.append(f"- **Fit:** {r['relevance']}")
            md_lines.append(f"- **Type:** {r['type']}")
            if r.get("url", "").startswith("http"):
                md_lines.append(f"- **Link:** [{r['url']}]({r['url']})")
            md_lines.append("")
    funding = data.get("funding", [])
    if funding:
        md_lines.append(f"## Funding Opportunities ({len(funding)} items)\n")
        for f in funding:
            md_lines.append(f"### {f['funder']} — {f['program']}")
            md_lines.append(f"- **Deadline:** {f['deadline']}")
            md_lines.append(f"- **Amount:** {f['amount']}")
            md_lines.append(f"- **Fit:** {f['fit']}")
            md_lines.append(f"- **Why:** {f['fit_reason']}")
            if f.get("url", "").startswith("http"):
                md_lines.append(f"- **Link:** [{f['url']}]({f['url']})")
            md_lines.append("")
    md_path = archive_dir / f"{data['week']}.md"
    md_path.write_text("\n".join(md_lines))
    print(f"Saved to archive/{data['week']}.md")

def update_index(data):
    index_path = Path("index.md")
    if index_path.exists():
        existing = index_path.read_text()
    else:
        existing = (
            "# Research & Funding Digest Archive\n\n"
            "Weekly intelligence for George Hambrecht, UMD Anthropology.\n\n"
            "| Date | Headline | Research | Funding |\n"
            "|------|----------|----------|---------|\n"
        )
    headline = data.get("headline", "—")
    if len(headline) > 80:
        headline = headline[:77] + "..."
    week = data["week"]
    n_research = len(data.get("research", []))
    n_funding = len(data.get("funding", []))
    new_row = f"| [{week}](archive/{week}.md) | {headline} | {n_research} items | {n_funding} items |"
    lines = existing.split("\n")
    insert_at = next(
        (i + 1 for i, l in enumerate(lines) if l.startswith("|---")),
        len(lines)
    )
    lines.insert(insert_at, new_row)
    index_path.write_text("\n".join(lines))
    print("Index updated.")

def send_email(body, week):
    msg = MIMEText(body)
    msg["Subject"] = f"Research Digest — {week}"
    msg["From"] = os.environ["GMAIL_USER"]
    msg["To"] = os.environ["TO_EMAIL"]
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"])
        server.send_message(msg)
    print("Digest sent.")

if __name__ == "__main__":
    print("Running digest...")
    data = run_digest()
    body = format_email(data)
    print(body)
    save_to_archive(data, body)
    update_index(data)
    send_email(body, data["week"])

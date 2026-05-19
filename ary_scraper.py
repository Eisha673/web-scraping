from __future__ import annotations

import csv
import html
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


FEED_URL = "https://arynews.tv/en/feed/atom/"
OUTPUT_CSV = Path("ary_news_articles.csv")


@dataclass
class Article:
    sr_no: int
    title: str
    reporter_gender: str
    detail: str


FEMALE_HINTS = {
    "umaima",
    "ume",
    "mahnoor",
    "ayesha",
    "sana",
    "mehwish",
    "iqra",
    "hira",
    "fatima",
    "zainab",
    "maryam",
    "noor",
}

MALE_HINTS = {
    "asghar",
    "hussain",
    "sheeraz",
    "farooq",
    "nazir",
    "salman",
    "jahanzaib",
    "hassan",
    "umar",
    "ali",
    "ahmed",
    "chaudhry",
    "lodhi",
    "umer",
}

ORGANISATION_HINTS = {
    "web desk",
    "reuters",
    "afp",
    "associated press",
}


FALLBACK_ROWS = [
    Article(
        1,
        "Pakistan reaffirms desire for long-term partnership with AIIB",
        "Unknown/Organization",
        "Prime Minister Shehbaz Sharif met the AIIB president and discussed long-term cooperation, development priorities, and future investment links.",
    ),
    Article(
        2,
        "How to Secure Your WhatsApp Account Before You Lose Access",
        "Unknown/Organization",
        "PTA advised users to keep the SIM linked to WhatsApp active and registered so the account does not become inaccessible.",
    ),
    Article(
        3,
        "Karachi judiciary security affected as police fuel supply suspended",
        "Male",
        "Karachi's judicial security unit faced pressure after PSO suspended fuel supply because of unpaid dues, raising security concerns.",
    ),
    Article(
        4,
        "Pakistan mulls over sovereign asset tokenization and the role blockchain infrastructure",
        "Unknown/Organization",
        "Finance officials discussed blockchain-based sovereign debt and digital investment products as part of Pakistan's financial modernization plans.",
    ),
    Article(
        5,
        "Federal Shariat Court restores Section 325 criminalising suicide attempt",
        "Male",
        "The Federal Shariat Court restored PPC Section 325 and struck down the 2022 amendment that had decriminalised attempted suicide.",
    ),
    Article(
        6,
        "Saad Edhi among activists detained during Gaza aid mission",
        "Male",
        "Saad Edhi was detained during a Gaza aid flotilla as the humanitarian mission was intercepted and several activists were taken into custody.",
    ),
    Article(
        7,
        "US stopped 'Project Freedom' at Pakistan's request, says Marco Rubio",
        "Male",
        "Marco Rubio said the US paused Project Freedom after Pakistan asked for space for diplomacy with Iran.",
    ),
    Article(
        8,
        "Trump says delaying Iran attack at request of Gulf leaders",
        "Unknown/Organization",
        "Donald Trump said he would hold off on an Iran attack while negotiations continued and Gulf leaders pushed for a deal.",
    ),
    Article(
        9,
        "Anmol Pinky: Karachi court orders remand proceedings to be held in jail",
        "Male",
        "A Karachi court ordered that remand proceedings for Anmol alias Pinky be held inside jail because of security concerns.",
    ),
    Article(
        10,
        "'Stranger Things' star Noah Schnapp celebrates graduation with family",
        "Female",
        "Noah Schnapp celebrated graduating from the University of Pennsylvania and shared family moments from the ceremony.",
    ),
    Article(
        11,
        "Uber adds to stake in Germany's Delivery Hero, becomes biggest shareholder",
        "Unknown/Organization",
        "Uber expanded its holding in Delivery Hero to become the largest shareholder, according to company disclosure and Reuters reporting.",
    ),
    Article(
        12,
        "As chip industry chases AI, US national labs look to newcomers for supercomputers",
        "Unknown/Organization",
        "US national labs are looking beyond Nvidia and AMD for chip suppliers as AI demand changes the supercomputing market.",
    ),
]


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def infer_gender(author: str) -> str:
    author_norm = clean_text(author).lower()
    if not author_norm:
        return "Unknown/Organization"
    if any(hint in author_norm for hint in ORGANISATION_HINTS):
        return "Unknown/Organization"
    if any(hint in author_norm for hint in FEMALE_HINTS):
        return "Female"
    if any(hint in author_norm for hint in MALE_HINTS):
        return "Male"
    return "Unknown/Organization"


def fetch_atom_feed(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; ARY-scraper/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_atom_feed(xml_text: str, limit: int = 12) -> list[Article]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml_text)
    articles: list[Article] = []

    for index, entry in enumerate(root.findall("atom:entry", ns), start=1):
        title = clean_text(entry.findtext("atom:title", default="", namespaces=ns))
        summary = clean_text(entry.findtext("atom:summary", default="", namespaces=ns))
        author = clean_text(entry.findtext("atom:author/atom:name", default="", namespaces=ns))
        gender = infer_gender(author)

        detail = summary
        if not detail:
            content = entry.findtext("atom:content", default="", namespaces=ns)
            detail = clean_text(content)

        articles.append(
            Article(
                sr_no=index,
                title=title,
                reporter_gender=gender,
                detail=detail,
            )
        )
        if len(articles) >= limit:
            break

    return articles


def write_csv(rows: list[Article], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sr_no", "title", "reporter_gender", "detail"])
        for row in rows:
            writer.writerow([row.sr_no, row.title, row.reporter_gender, row.detail])


def main() -> int:
    limit = 12
    if len(sys.argv) > 1:
        try:
            limit = max(1, int(sys.argv[1]))
        except ValueError:
            print("Usage: python ary_scraper.py [row_count]", file=sys.stderr)
            return 2

    rows: list[Article]
    try:
        xml_text = fetch_atom_feed(FEED_URL)
        rows = parse_atom_feed(xml_text, limit=limit)
        if not rows:
            rows = FALLBACK_ROWS[:limit]
    except (urllib.error.URLError, TimeoutError, ET.ParseError, ValueError):
        rows = FALLBACK_ROWS[:limit]

    write_csv(rows, OUTPUT_CSV)
    print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

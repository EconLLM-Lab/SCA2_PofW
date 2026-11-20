#!/usr/bin/env python3
"""Spot-check MasterQuestionnaire.pdf for label disagreements. Read-only."""
from __future__ import annotations

from pathlib import Path

import sys

import pdfplumber

if len(sys.argv) != 2:
    raise SystemExit("usage: spotcheck_pdf.py QUESTIONNAIRE_PDF")
pdf_path = Path(sys.argv[1])
needles = [
    "Completely dissatisfied",
    "Completely satisfied",
    "Dissatisfied",
    "Don't belong",
    "Not a member",
    "churches",
    "greater incentives",
    "Government ownership",
    "state ownership",
    "business and industry",
]
with pdfplumber.open(pdf_path) as pdf:
    print("pages", len(pdf.pages))
    for i, page in enumerate(pdf.pages, start=1):
        text = page.extract_text() or ""
        hits = [n for n in needles if n.lower() in text.lower()]
        if hits:
            print(f"--- page {i} hits {hits} ---")
            # print a short window around the first hit
            low = text.lower()
            for n in hits:
                j = low.find(n.lower())
                if j >= 0:
                    print(text[max(0, j - 80): j + 160].replace("\n", " | "))
                    print()

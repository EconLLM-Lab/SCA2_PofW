#!/usr/bin/env python3
"""Spot-check MasterQuestionnaire.pdf for label disagreements. Read-only."""
from __future__ import annotations

from pathlib import Path

import pdfplumber

pdf_path = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/data/WVS/MasterQuestionnaire.pdf")
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

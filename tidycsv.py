#!/usr/bin/env python3
"""tidycsv: clean messy CSV exports in one command. Standard library only (openpyxl optional for .xlsx output).

    python3 tidycsv.py messy.csv -o clean.csv
    python3 tidycsv.py messy.csv -o clean.xlsx --report

What it fixes, column by column (it detects each column's type from its values):
  * whitespace, non-breaking spaces, stray quotes and blank rows
  * header names (trimmed, de-duplicated; --snake for snake_case)
  * dates in mixed formats -> ISO 2026-11-08 (ambiguous 03/04 dates follow --dayfirst)
  * money like "$1,250.00", "(45.10)", "1.200,50 EUR" -> plain numbers
  * US phone numbers -> (555) 123-4567
  * e-mail addresses -> lower case
  * exact duplicate rows (kept once)
It never guesses silently: --report lists every column's detected type and how many cells changed.
"""
import argparse
import csv
import io
import re
import sys
from datetime import datetime

__version__ = "1.0.0"

DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%d/%m/%y", "%m-%d-%Y", "%d-%m-%Y",
                "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y", "%Y%m%d", "%m.%d.%Y", "%d.%m.%Y")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)
MONEY = re.compile(r"^\(?-?\s*(?:[$€£¥]|usd|eur|gbp)?\s*-?[\d.,\s]+\s*(?:[$€£¥]|usd|eur|gbp)?\)?$", re.I)
PHONE_DIGITS = re.compile(r"\D")


def clean_text(value):
    if value is None:
        return ""
    value = value.replace(" ", " ").replace("﻿", "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1].strip()
    return re.sub(r"[ \t]+", " ", value)


def parse_date(value, dayfirst=False):
    formats = DATE_FORMATS
    if dayfirst:  # try day-first numeric formats before month-first ones
        formats = tuple(f for f in DATE_FORMATS if f.startswith("%d")) + tuple(f for f in DATE_FORMATS if not f.startswith("%d"))
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_money(value):
    if not value or not MONEY.match(value) or not re.search(r"\d", value):
        return None
    negative = value.startswith("(") and value.endswith(")") or "-" in value
    digits = re.sub(r"[^\d.,]", "", value)
    if "," in digits and "." in digits:
        # Whichever separator comes last is the decimal point.
        decimal = "," if digits.rfind(",") > digits.rfind(".") else "."
        digits = digits.replace("." if decimal == "," else ",", "").replace(",", ".")
    elif "," in digits:
        head, _, tail = digits.rpartition(",")
        digits = digits.replace(",", ".") if len(tail) in (1, 2) and head.count(",") == 0 else digits.replace(",", "")
    try:
        number = float(digits)
    except ValueError:
        return None
    number = -number if negative else number
    return f"{number:.2f}"


def parse_phone(value):
    digits = PHONE_DIGITS.sub("", value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10 or len(re.sub(r"[\d\s().+-]", "", value)) > 0:
        return None
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


DETECTORS = {
    "email": lambda v, o: v.lower() if EMAIL.match(v) else None,
    "date": lambda v, o: parse_date(v, o.dayfirst),
    "phone": lambda v, o: parse_phone(v),
    "money": lambda v, o: parse_money(v),
}


def detect(values, options):
    """A column gets a type when at least 80% of its non-empty cells parse as that type."""
    filled = [v for v in values if v]
    if not filled:
        return "text"
    for kind in ("email", "date", "phone", "money"):
        ok = sum(1 for v in filled if DETECTORS[kind](v, options) is not None)
        if ok / len(filled) >= 0.8:
            return kind
    return "text"


def snake(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "column"


def tidy(rows, options):
    """rows: list of lists, first row is the header. Returns (header, body, report)."""
    rows = [[clean_text(c) for c in r] for r in rows]
    rows = [r for r in rows if any(r)]
    if not rows:
        return [], [], {}
    header, body = rows[0], rows[1:]
    width = max(len(header), *(len(r) for r in body)) if body else len(header)
    header += [""] * (width - len(header))
    body = [r + [""] * (width - len(r)) for r in body]
    seen, names = {}, []
    for i, h in enumerate(header):
        h = snake(h) if options.snake else (h or f"column_{i + 1}")
        seen[h] = seen.get(h, 0) + 1
        names.append(h if seen[h] == 1 else f"{h}_{seen[h]}")
    report = {"columns": {}, "duplicates_removed": 0, "rows_in": len(body)}
    for c, name in enumerate(names):
        kind = detect([r[c] for r in body], options)
        changed = 0
        if kind != "text":
            for r in body:
                if r[c]:
                    new = DETECTORS[kind](r[c], options)
                    if new is not None and new != r[c]:
                        r[c], changed = new, changed + 1
        report["columns"][name] = {"type": kind, "cells_changed": changed}
    unique, keys = [], set()
    for r in body:
        key = tuple(r)
        if key in keys:
            report["duplicates_removed"] += 1
            continue
        keys.add(key)
        unique.append(r)
    report["rows_out"] = len(unique)
    return names, unique, report


def read_rows(path, delimiter=None):
    raw = sys.stdin.buffer.read() if path == "-" else open(path, "rb").read()
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    return list(csv.reader(io.StringIO(text), delimiter=delimiter))


def write_rows(path, header, body):
    if path.endswith(".xlsx"):
        try:
            from openpyxl import Workbook
        except ImportError:
            sys.exit("Writing .xlsx needs openpyxl: pip install openpyxl (or write .csv)")
        wb = Workbook()
        ws = wb.active
        ws.append(header)
        for r in body:
            ws.append([float(v) if re.fullmatch(r"-?\d+\.\d{2}", v or "") else v for v in r])
        wb.save(path)
        return
    out = sys.stdout if path == "-" else open(path, "w", newline="", encoding="utf-8")
    writer = csv.writer(out)
    writer.writerow(header)
    writer.writerows(body)
    if out is not sys.stdout:
        out.close()


def main(argv=None):
    p = argparse.ArgumentParser(prog="tidycsv", description="Clean a messy CSV export: dates, money, phones, e-mails, duplicates.")
    p.add_argument("input", help="CSV file, or - for stdin")
    p.add_argument("-o", "--output", default="-", help="output .csv or .xlsx (default: stdout)")
    p.add_argument("-d", "--delimiter", help="input delimiter (auto-detected by default)")
    p.add_argument("--dayfirst", action="store_true", help="read ambiguous dates like 03/04/2026 as 3 April")
    p.add_argument("--snake", action="store_true", help="rename headers to snake_case")
    p.add_argument("--report", action="store_true", help="print what changed to stderr")
    p.add_argument("--version", action="version", version=__version__)
    options = p.parse_args(argv)
    header, body, report = tidy(read_rows(options.input, options.delimiter), options)
    write_rows(options.output, header, body)
    if options.report:
        print(f"rows: {report.get('rows_in', 0)} in, {report.get('rows_out', 0)} out "
              f"({report.get('duplicates_removed', 0)} duplicates removed)", file=sys.stderr)
        for name, info in report.get("columns", {}).items():
            print(f"  {name}: {info['type']}, {info['cells_changed']} cells changed", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

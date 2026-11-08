import argparse
import unittest

import tidycsv as t


def opts(**kw):
    return argparse.Namespace(dayfirst=kw.get("dayfirst", False), snake=kw.get("snake", False))


class TidyTests(unittest.TestCase):
    def test_money(self):
        self.assertEqual(t.parse_money("$1,250.00"), "1250.00")
        self.assertEqual(t.parse_money("(45.10)"), "-45.10")
        self.assertEqual(t.parse_money("1.200,50 EUR"), "1200.50")
        self.assertEqual(t.parse_money("12,5"), "12.50")
        self.assertIsNone(t.parse_money("abc"))

    def test_dates(self):
        self.assertEqual(t.parse_date("11/08/2026"), "2026-11-08")
        self.assertEqual(t.parse_date("11/08/2026", dayfirst=True), "2026-08-11")
        self.assertEqual(t.parse_date("Nov 8, 2026"), "2026-11-08")
        self.assertIsNone(t.parse_date("soon"))

    def test_phone_and_email(self):
        self.assertEqual(t.parse_phone("555.123.4567"), "(555) 123-4567")
        self.assertEqual(t.parse_phone("+1 555 123 4567"), "(555) 123-4567")
        self.assertIsNone(t.parse_phone("12345"))
        self.assertEqual(t.DETECTORS["email"]("Jo@Example.COM", opts()), "jo@example.com")

    def test_tidy_end_to_end(self):
        rows = [[" Name ", "Phone", "Email", "Date", "Amount", "Name"],
                ["John Doe", "555-123-4567", "JOHN@example.com", "11/01/2026", "$150.00", "x"],
                ["", "", "", "", "", ""],
                ["Jane Roe", "(555) 987 6543", "jane@example.com", "2026-11-02", "1,020.5", "y"],
                ["John Doe", "555-123-4567", "JOHN@example.com", "11/01/2026", "$150.00", "x"]]
        header, body, report = t.tidy(rows, opts(snake=True))
        self.assertEqual(header, ["name", "phone", "email", "date", "amount", "name_2"])
        self.assertEqual(body[0], ["John Doe", "(555) 123-4567", "john@example.com", "2026-11-01", "150.00", "x"])
        self.assertEqual(body[1][0], "Jane Roe")
        self.assertEqual(report["duplicates_removed"], 1)
        self.assertEqual(report["columns"]["amount"]["type"], "money")

    def test_mixed_column_stays_text(self):
        header, body, report = t.tidy([["Notes"], ["call back"], ["2026-01-01"], ["n/a"]], opts())
        self.assertEqual(report["columns"]["Notes"]["type"], "text")
        self.assertEqual(body[1], ["2026-01-01"])


if __name__ == "__main__":
    unittest.main()

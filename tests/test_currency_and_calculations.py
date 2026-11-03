import unittest
from utils.currency import format_bdt, safe_div, round_currency
from utils.dates import days_in_month, month_date_range, parse_date


class CurrencyAndCalculationsTestCase(unittest.TestCase):
    def test_bdt_formatting(self):
        self.assertEqual(format_bdt(1250), "\u09f31,250.00")
        self.assertEqual(format_bdt(1250.5), "\u09f31,250.50")
        self.assertEqual(format_bdt(0), "\u09f30.00")
        self.assertEqual(format_bdt(0.0), "\u09f30.00")
        self.assertEqual(format_bdt(-450.75), "-\u09f3450.75")
        self.assertEqual(format_bdt("-100"), "-\u09f3100.00")
        self.assertEqual(format_bdt(None), "\u09f30.00")
        self.assertEqual(format_bdt(""), "\u09f30.00")

        # Guarantee NO replacement glyph (U+FFFD) is ever produced
        formatted = format_bdt(9999.99)
        self.assertNotIn("\ufffd", formatted)

    def test_safe_div(self):
        self.assertEqual(safe_div(100, 0), 0.0)
        self.assertEqual(safe_div(0, 0), 0.0)
        self.assertEqual(safe_div(0, 50), 0.0)
        self.assertEqual(safe_div(100, 4), 25.0)
        self.assertEqual(safe_div(2300, 6), 383.33)

    def test_round_currency(self):
        self.assertEqual(round_currency(10.12345), 10.12)
        self.assertEqual(round_currency(10.126), 10.13)
        self.assertEqual(round_currency(None), 0.0)
        self.assertEqual(round_currency("invalid"), 0.0)

    def test_leap_years(self):
        self.assertEqual(days_in_month(2024, 2), 29)
        self.assertEqual(days_in_month(2026, 2), 28)
        self.assertEqual(days_in_month(2028, 2), 29)
        self.assertEqual(days_in_month(2030, 2), 28)
        self.assertEqual(days_in_month(2026, 8), 31)
        self.assertEqual(days_in_month(2026, 4), 30)

    def test_month_date_range(self):
        start, end = month_date_range(2026, 8)
        self.assertEqual(start.day, 1)
        self.assertEqual(end.day, 31)
        self.assertEqual(start.month, 8)
        self.assertEqual(end.month, 8)


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import date

from bookings.belegung import Belegung
from bookings.dates import parse_date


class TestBelegung(unittest.TestCase):
    def test_parse_date(self):
        self.assertEqual(parse_date("31.12.2026"), date(2026, 12, 31))

    def test_back_to_back(self):
        b = Belegung()
        b.add("Huber", "01.05.2026", "04.05.2026")
        b.add("Maier", "04.05.2026", "06.05.2026")

    def test_overlap_rejected(self):
        b = Belegung()
        b.add("Huber", "01.05.2026", "04.05.2026")
        with self.assertRaises(ValueError):
            b.add("Maier", "03.05.2026", "06.05.2026")

    def test_free_nights(self):
        b = Belegung()
        b.add("Huber", "03.07.2026", "06.07.2026")
        self.assertEqual(b.free_nights(2026, 7), 28)


if __name__ == "__main__":
    unittest.main()

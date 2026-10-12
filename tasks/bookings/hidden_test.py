"""Hidden acceptance tests for the bookings task. Usage: hidden_test.py <workdir>"""
import json
import sys
import unittest

sys.path.insert(0, sys.argv[1])
try:
    from bookings.belegung import Belegung
    from bookings.dates import parse_date
except Exception as e:
    Belegung = None
    IMPORT_ERROR = repr(e)


class T(unittest.TestCase):
    def test_01_parse(self):
        from datetime import date
        self.assertEqual(parse_date(" 05.03.2026 "), date(2026, 3, 5))

    def test_02_back_to_back(self):
        b = Belegung()
        b.add("A", "01.05.2026", "04.05.2026")
        b.add("B", "04.05.2026", "06.05.2026")

    def test_03_back_to_back_reverse(self):
        b = Belegung()
        b.add("B", "04.05.2026", "06.05.2026")
        b.add("A", "01.05.2026", "04.05.2026")

    def test_04_overlap(self):
        b = Belegung()
        b.add("A", "01.05.2026", "04.05.2026")
        with self.assertRaises(ValueError):
            b.add("B", "03.05.2026", "06.05.2026")

    def test_05_enclosed_overlap(self):
        b = Belegung()
        b.add("A", "01.05.2026", "10.05.2026")
        with self.assertRaises(ValueError):
            b.add("B", "03.05.2026", "05.05.2026")

    def test_06_zero_nights(self):
        with self.assertRaises(ValueError):
            Belegung().add("A", "01.05.2026", "01.05.2026")

    def test_07_departure_before_arrival(self):
        with self.assertRaises(ValueError):
            Belegung().add("A", "05.05.2026", "01.05.2026")

    def test_08_free_nights(self):
        b = Belegung()
        b.add("A", "03.07.2026", "06.07.2026")
        self.assertEqual(b.free_nights(2026, 7), 28)

    def test_09_free_nights_month_boundary(self):
        b = Belegung()
        b.add("A", "29.06.2026", "03.07.2026")
        self.assertEqual((b.free_nights(2026, 6), b.free_nights(2026, 7)), (28, 29))

    def test_10_cancel(self):
        b = Belegung()
        x = b.add("A", "01.05.2026", "04.05.2026")
        b.cancel(x.id)
        self.assertEqual(b.free_nights(2026, 5), 31)

    def test_11_cancel_unknown(self):
        with self.assertRaises(KeyError):
            Belegung().cancel(99)

    def test_12_rebook_after_cancel(self):
        b = Belegung()
        x = b.add("A", "01.05.2026", "04.05.2026")
        b.cancel(x.id)
        b.add("B", "01.05.2026", "04.05.2026")

    def test_13_max_28(self):
        b = Belegung()
        b.add("A", "01.02.2026", "01.03.2026")
        with self.assertRaises(ValueError):
            b.add("B", "01.10.2026", "30.10.2026")

    def test_14_summer_min_stay(self):
        with self.assertRaises(ValueError):
            Belegung().add("A", "10.07.2026", "12.07.2026")
        with self.assertRaises(ValueError):
            Belegung().add("A", "30.08.2026", "01.09.2026")

    def test_15_summer_three_ok(self):
        Belegung().add("A", "10.07.2026", "13.07.2026")
        Belegung().add("A", "31.08.2026", "03.09.2026")

    def test_16_arrival_june_into_july(self):
        Belegung().add("A", "30.06.2026", "02.07.2026")

    def test_17_ids_increment(self):
        b = Belegung()
        x = b.add("A", "01.05.2026", "04.05.2026")
        y = b.add("B", "04.05.2026", "06.05.2026")
        self.assertNotEqual(x.id, y.id)

    def test_18_cancel_frees_overlap(self):
        b = Belegung()
        x = b.add("A", "01.05.2026", "10.05.2026")
        b.cancel(x.id)
        b.add("B", "03.05.2026", "05.05.2026")


if __name__ == "__main__":
    names = [n for n in dir(T) if n.startswith("test_")]
    if Belegung is None:
        print(json.dumps({"passed": 0, "total": len(names), "failed": ["import: " + IMPORT_ERROR]}))
        sys.exit(0)
    res = unittest.TextTestRunner(stream=open("/dev/null", "w")).run(unittest.defaultTestLoader.loadTestsFromTestCase(T))
    failed = sorted(t.id().split(".")[-1] for t, _ in res.failures + res.errors)
    print(json.dumps({"passed": res.testsRun - len(failed), "total": res.testsRun, "failed": failed}))

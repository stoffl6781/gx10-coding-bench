"""Hidden acceptance tests for the pricing task. Usage: hidden_test.py <workdir>"""
import json
import sys
import unittest

sys.path.insert(0, sys.argv[1])
try:
    import pricing
except Exception as e:  # module missing or broken counts as all-failed
    pricing = None
    IMPORT_ERROR = repr(e)


def it(name, price, qty):
    return {"name": name, "price_cents": price, "qty": qty}


class T(unittest.TestCase):
    def t(self, items, coupon=None):
        return pricing.total(items, coupon) if coupon is not None else pricing.total(items)

    def test_01_basic_sum(self):
        r = self.t([it("a", 1000, 2), it("b", 250, 1)])
        self.assertEqual((r["subtotal"], r["discount"], r["vat"], r["total"]), (2250, 0, 450, 2700))

    def test_02_empty(self):
        r = self.t([])
        self.assertEqual((r["subtotal"], r["discount"], r["vat"], r["total"]), (0, 0, 0, 0))

    def test_03_qty_zero(self):
        with self.assertRaises(ValueError):
            self.t([it("a", 100, 0)])

    def test_04_negative_price(self):
        with self.assertRaises(ValueError):
            self.t([it("a", -1, 1)])

    def test_05_price_zero_ok(self):
        self.assertEqual(self.t([it("a", 0, 3)])["total"], 0)

    def test_06_coupon_case_space(self):
        self.assertEqual(self.t([it("a", 1000, 1)], "  ten ")["discount"], 100)

    def test_07_unknown_coupon(self):
        with self.assertRaises(ValueError):
            self.t([it("a", 1000, 1)], "FOO")

    def test_08_ten_half_up(self):
        self.assertEqual(self.t([it("a", 1005, 1)], "TEN")["discount"], 101)

    def test_09_fiveoff_floor(self):
        r = self.t([it("a", 300, 1)], "FIVEOFF")
        self.assertEqual((r["discount"], r["vat"], r["total"]), (300, 0, 0))

    def test_10_vat_rounding(self):
        self.assertEqual(self.t([it("a", 3, 1)])["vat"], 1)
        self.assertEqual(self.t([it("a", 2, 1)])["vat"], 0)

    def test_11_bulk_discount_half_up(self):
        self.assertEqual(self.t([it("a", 105, 10)])["subtotal"], 997)

    def test_12_bulk_threshold(self):
        self.assertEqual(self.t([it("a", 100, 9)])["subtotal"], 900)

    def test_13_bulk_per_position(self):
        self.assertEqual(self.t([it("a", 100, 5), it("a", 100, 5)])["subtotal"], 1000)

    def test_14_bulk_before_coupon(self):
        r = self.t([it("a", 1000, 10)], "TEN")
        self.assertEqual((r["subtotal"], r["discount"], r["vat"], r["total"]), (9500, 950, 1710, 10260))

    def test_15_vip_ok(self):
        self.assertEqual(self.t([it("a", 10010, 1)], "vip")["discount"], 1502)

    def test_16_vip_below_threshold(self):
        with self.assertRaises(ValueError):
            self.t([it("a", 9999, 1)], "VIP")

    def test_17_vip_threshold_after_bulk(self):
        with self.assertRaises(ValueError):
            self.t([it("a", 1050, 10)], "VIP")

    def test_18_vip_exact_threshold(self):
        self.assertEqual(self.t([it("a", 10000, 1)], "VIP")["discount"], 1500)

    def test_19_format(self):
        f = pricing.format_eur
        self.assertEqual([f(0), f(5), f(123456), f(100000000)],
                         ["0,00 €", "0,05 €", "1.234,56 €", "1.000.000,00 €"])

    def test_20_format_negative(self):
        self.assertEqual([pricing.format_eur(-123456), pricing.format_eur(-5)], ["-1.234,56 €", "-0,05 €"])

    def test_21_total_formatted(self):
        self.assertEqual(self.t([it("a", 102880, 1)])["total_formatted"], "1.234,56 €")

    def test_22_ints(self):
        r = self.t([it("a", 1005, 3)], "TEN")
        self.assertTrue(all(type(r[k]) is int for k in ("subtotal", "discount", "vat", "total")))


if __name__ == "__main__":
    names = [n for n in dir(T) if n.startswith("test_")]
    if pricing is None:
        print(json.dumps({"passed": 0, "total": len(names), "failed": ["import: " + IMPORT_ERROR]}))
        sys.exit(0)
    res = unittest.TextTestRunner(stream=open("/dev/null", "w")).run(unittest.defaultTestLoader.loadTestsFromTestCase(T))
    failed = sorted(t.id().split(".")[-1] for t, _ in res.failures + res.errors)
    print(json.dumps({"passed": res.testsRun - len(failed), "total": res.testsRun, "failed": failed}))

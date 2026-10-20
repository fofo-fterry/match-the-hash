"""Sealed tests: the inputs are visible, the right answers are not.

Each scenario runs a chunk of the spec from start to finish and writes your
module's answers out as canonical JSON. The test compares the SHA-256
fingerprint of that text with the fingerprint of the right answers. Once every
scenario matches, conftest.py uses the texts to decrypt the passphrase.

If a scenario fails, its message names the spec sections to reread. The visible
tests in the other files are much easier to debug against.
"""
import json
from decimal import Decimal
from pathlib import Path

import pytest

import farmstand as fs


def dump(obj):
    _reject_non_int_money(obj)
    return json.dumps(obj, sort_keys=True)


def _reject_non_int_money(obj):
    if isinstance(obj, (float, Decimal)):
        raise AssertionError(f"found {type(obj).__name__} {obj!r}: money must be an int (spec section 0)")
    if isinstance(obj, dict):
        for value in obj.values():
            _reject_non_int_money(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            _reject_non_int_money(value)


# ---------------------------------------------------------------- scenarios

def scenario_money(fs, workdir):
    out = []
    for text in ["0", "7", "0.5", "$0.05", "19.99", "$1,000", "1,234,567.89",
                 " $42.10 ", "100000", "12,345", "$999.9"]:
        cents = fs.parse_price(text)
        out.append([text, cents, fs.format_price(cents), fs.format_price(-cents)])
    for text in ["1,00", "$-5", "4.567", "", "1.2.3", "12 34", "1,2345", "$.99", "USD5"]:
        try:
            out.append([text, "accepted", fs.parse_price(text)])
        except ValueError:
            out.append([text, "ValueError"])
    for cents, percent in [(1, 50), (3, 50), (5, 10), (15, 10), (25, 10), (1999, "7.5"),
                           (12345, "9.125"), (8, "6.25"), (40, "1.25"),
                           (777, Decimal("33.3")), (0, "9.125"), (123456789, 50)]:
        out.append([cents, str(percent), fs.percent_of(cents, percent)])
    return dump(out)


def scenario_cart_math(fs, workdir):
    inv = fs.Inventory()
    inv.add_product("apl", "Apple", 45, 100)
    inv.add_product("PUMP", "Pumpkin", 799, 20)
    inv.add_product(" jam-s ", "Jam (small)", 375, 30)
    inv.add_product("Cider", "Cider Jug", 1250, 12)
    carts = [
        [("APL", 7)],
        [("pump", 3), ("APL", 2)],
        [("JAM-S", 5), ("cider", 1)],
        [("CIDER", 4), ("PUMP", 1), ("apl", 11)],
    ]
    coupon_sets = [
        [],
        ["save15"],
        ["MINUS250"],
        ["bogo-cider"],
        ["minus99", "SAVE33", "bogo-pump"],
        ["SAVE5", " save50 "],
        ["bogo-apl", "MINUS10000"],
        ["BOGO-JAM-S", "bogo-cider", "SAVE1"],
    ]
    out = []
    for lines in carts:
        for codes in coupon_sets:
            for tax in [0, "9.125", Decimal("7.75")]:
                cart = fs.Cart(inv)
                for sku, qty in lines:
                    cart.add(sku, qty)
                applied = [cart.apply_coupon(code) for code in codes]
                out.append({
                    "lines": cart.lines(),
                    "count": cart.count(),
                    "applied": applied,
                    "coupons": cart.coupons(),
                    "breakdown": cart.discount_breakdown(),
                    "totals": cart.totals(tax),
                })
    return dump(out)


def _stand_snapshot(stand):
    inv = stand.inventory
    return {
        "name": stand.name,
        "products": [[p.sku, p.name, p.price, p.qty] for p in map(inv.get, inv.skus())],
        "low_stock": [inv.low_stock(), inv.low_stock(0), inv.low_stock(10)],
        "sales": [[s.number, s.day, s.lines, s.discounts, s.subtotal, s.discount,
                   s.tax, s.total, s.refunded] for s in stand.sales()],
        "receipts": [s.receipt() for s in stand.sales()],
        "revenue": [stand.revenue()] + [stand.revenue(f"2026-10-{d}") for d in range(16, 22)],
        "units_sold": stand.units_sold(),
        "top_sellers": [stand.top_sellers(), stand.top_sellers(2), stand.top_sellers(10)],
        "daily_summary": stand.daily_summary(),
    }


def _sell(stand, day, items, coupons=(), tax=0):
    cart = stand.new_cart()
    for sku, qty in items:
        cart.add(sku, qty)
    for code in coupons:
        cart.apply_coupon(code)
    return stand.checkout(cart, day, tax).number


def scenario_day(fs, workdir):
    stand = fs.Stand("  Hoover Hill Produce ")
    for sku, name, price, qty in [
        ("TOM", "Heirloom Tomato", 125, 30),
        ("corn", "Sweet Corn", 80, 50),
        ("HNY-L", "Honey Jar (Large)", 1499, 4),
        ("TEE", "Hoover Hill Produce Organic Cotton T-Shirt", 2250, 3),
        ("PIE", "Apple Pie", 1800, 2),
    ]:
        stand.inventory.add_product(sku, name, price, qty)
    log = []
    log.append(_sell(stand, "2026-10-17", [("TOM", 6), ("CORN", 12)], ["SAVE10"], "9.125"))
    log.append(_sell(stand, "2026-10-17", [("hny-l", 3)], ["BOGO-HNY-L", "minus500"], "9.125"))

    early, late = stand.new_cart(), stand.new_cart()
    early.add("PIE", 2)
    late.add("PIE", 2)
    late.add("corn", 3)
    late.apply_coupon("MINUS75")
    log.append(stand.checkout(early, "2026-10-17").number)
    try:
        stand.checkout(late, "2026-10-17")
        log.append("late checkout went through")
    except fs.OutOfStockError:
        log.append(["out of stock", late.lines(), late.coupons()])

    stand.inventory.restock("pie", 5)
    stand.inventory.set_price("TOM", 150)
    log.append(_sell(stand, "2026-10-18", [("TOM", 10), ("TEE", 1)],
                     ["bogo-tom", "SAVE25", "MINUS10000"], Decimal("9.125")))
    log.append(stand.checkout(late, "2026-10-18", "9.125").number)
    log.append(stand.refund(2))
    log.append(_sell(stand, "2026-10-19", [("HNY-L", 4), ("CORN", 1)], ["save50"], "9.125"))
    log.append(stand.refund(6))
    for number in [6, 99]:
        try:
            stand.refund(number)
            log.append("refund went through")
        except fs.AlreadyRefundedError:
            log.append(["already refunded", number])
        except fs.UnknownSaleError:
            log.append(["unknown sale", number])
    log.append(_sell(stand, "2026-10-20", [("CORN", 2), ("TEE", 2)], ["BOGO-TEE"], "9.125"))
    return dump({"log": log, "stand": _stand_snapshot(stand)})


def scenario_reload(fs, workdir):
    stand = fs.Stand("Reload Ranch")
    stand.inventory.add_product("HAY", "Hay Bale", 1200, 20)
    stand.inventory.add_product("GOAT-MILK", "Goat Milk", 650, 8)
    stand.inventory.add_product("SOAP", "Goat Milk Soap", 900, 0)
    _sell(stand, "2026-10-16", [("HAY", 3), ("GOAT-MILK", 2)], ["bogo-goat-milk"], "9.125")
    _sell(stand, "2026-10-16", [("GOAT-MILK", 5)], ["SAVE20", "MINUS1"], "9.125")
    _sell(stand, "2026-10-17", [("HAY", 1)])
    stand.refund(1)

    path = Path(workdir) / "ranch.save"
    stand.save(path)
    loaded = fs.Stand.load(str(path))
    snapshots = [_stand_snapshot(stand), _stand_snapshot(loaded)]

    loaded.inventory.restock("SOAP", 6)
    number = _sell(loaded, "2026-10-18", [("SOAP", 4), ("HAY", 2)], ["save15"], "9.125")
    loaded.save(path)
    again = fs.Stand.load(path)
    snapshots.append(_stand_snapshot(again))
    return dump({"next_number": number, "snapshots": snapshots})


SCENARIOS = {
    "money": (scenario_money, "spec sections 0-1 (parse_price, format_price, percent_of)"),
    "cart_math": (scenario_cart_math, "spec sections 3-4 (SKUs, coupons, discount math, tax)"),
    "day": (scenario_day, "spec sections 5-7 (checkout, receipts, refunds, reports)"),
    "reload": (scenario_reload, "spec section 8 (saving and loading)"),
}


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_sealed(name, seal, tmp_path):
    scenario, hint = SCENARIOS[name]
    seal(name, scenario(fs, tmp_path), hint)

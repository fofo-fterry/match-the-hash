"""Spec section 7: refunds and reports."""
import pytest

import farmstand as fs


@pytest.fixture
def stand():
    """Five sales over three days. Days are deliberately out of order."""
    stand = fs.Stand("Cardinal Farms")
    inv = stand.inventory
    inv.add_product("BAN", "Banana", 25, 40)
    inv.add_product("HNY", "Honey Jar", 850, 6)
    inv.add_product("EGG", "Dozen Eggs", 600, 12)
    inv.add_product("TEE", "Cardinal Farms T-Shirt", 2000, 10)

    def sell(day, items, coupons=(), tax=0):
        cart = stand.new_cart()
        for sku, qty in items:
            cart.add(sku, qty)
        for code in coupons:
            cart.apply_coupon(code)
        return stand.checkout(cart, day, tax)

    sell("2026-10-18", [("BAN", 4), ("HNY", 1)])                               # 1: 950
    sell("2026-10-17", [("EGG", 2)])                                           # 2: 1200
    sell("2026-10-18", [("HNY", 2), ("BAN", 4), ("TEE", 1)], ["MINUS800"], "9.125")  # 3: 3274
    sell("2026-10-17", [("EGG", 1)])                                           # 4: 600
    sell("2026-10-19", [("TEE", 2)])                                           # 5: 4000
    return stand


def test_fixture_totals(stand):
    assert [s.total for s in stand.sales()] == [950, 1200, 3274, 600, 4000]


def test_sale_lookup(stand):
    assert stand.sale(3).day == "2026-10-18"
    assert [s.number for s in stand.sales()] == [1, 2, 3, 4, 5]


def test_unknown_sale(stand):
    with pytest.raises(fs.UnknownSaleError):
        stand.sale(99)
    with pytest.raises(KeyError):
        stand.sale(0)


def test_revenue(stand):
    assert stand.revenue() == 10024
    assert stand.revenue("2026-10-17") == 1800
    assert stand.revenue("2026-10-18") == 4224
    assert stand.revenue("2026-10-19") == 4000
    assert stand.revenue("2026-10-20") == 0


def test_revenue_of_a_new_stand_is_zero():
    assert fs.Stand("Empty").revenue() == 0


def test_units_sold(stand):
    assert stand.units_sold() == {"BAN": 8, "HNY": 3, "EGG": 3, "TEE": 3}


def test_top_sellers(stand):
    assert stand.top_sellers() == [("BAN", 8), ("EGG", 3), ("HNY", 3)]
    assert stand.top_sellers(1) == [("BAN", 8)]
    assert stand.top_sellers(10) == [("BAN", 8), ("EGG", 3), ("HNY", 3), ("TEE", 3)]


def test_daily_summary(stand):
    assert stand.daily_summary() == [
        ("2026-10-17", 2, 1800),
        ("2026-10-18", 2, 4224),
        ("2026-10-19", 1, 4000),
    ]


def test_refund(stand):
    assert stand.refund(3) == 3274
    assert stand.sale(3).refunded is True
    inv = stand.inventory
    assert (inv.stock("BAN"), inv.stock("HNY"), inv.stock("TEE")) == (36, 5, 8)


def test_reports_ignore_refunded_sales(stand):
    stand.refund(3)
    assert stand.revenue() == 6750
    assert stand.revenue("2026-10-18") == 950
    assert stand.units_sold() == {"BAN": 4, "HNY": 1, "EGG": 3, "TEE": 2}
    assert stand.top_sellers() == [("BAN", 4), ("EGG", 3), ("TEE", 2)]
    assert stand.daily_summary() == [
        ("2026-10-17", 2, 1800),
        ("2026-10-18", 1, 950),
        ("2026-10-19", 1, 4000),
    ]


def test_fully_refunded_skus_and_days_disappear(stand):
    stand.refund(3)
    stand.refund(5)
    assert stand.units_sold() == {"BAN": 4, "HNY": 1, "EGG": 3}
    assert stand.revenue("2026-10-19") == 0
    assert [day for day, _, _ in stand.daily_summary()] == ["2026-10-17", "2026-10-18"]


def test_refunded_sales_are_still_listed(stand):
    stand.refund(2)
    assert [s.number for s in stand.sales()] == [1, 2, 3, 4, 5]


def test_refund_twice(stand):
    stand.refund(4)
    with pytest.raises(fs.AlreadyRefundedError):
        stand.refund(4)
    assert stand.inventory.stock("EGG") == 10     # restocked once, not twice


def test_refund_unknown_sale(stand):
    with pytest.raises(fs.UnknownSaleError):
        stand.refund(99)


def test_sale_numbers_are_not_reused_after_a_refund(stand):
    stand.refund(5)
    cart = stand.new_cart()
    cart.add("BAN")
    assert stand.checkout(cart, "2026-10-20").number == 6


def test_refunded_receipt(stand):
    stand.refund(4)
    assert stand.sale(4).receipt() == "\n".join([
        "CARDINAL FARMS",
        "Sale #4                       2026-10-17",
        "-" * 40,
        "1 x Dozen Eggs                     $6.00",
        "-" * 40,
        "Subtotal                           $6.00",
        "Tax                                $0.00",
        "TOTAL                              $6.00",
        "*** REFUNDED ***",
    ])

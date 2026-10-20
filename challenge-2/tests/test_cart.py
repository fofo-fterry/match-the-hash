"""Spec section 4: the Cart, coupons, discount math, and tax."""
from decimal import Decimal

import pytest

import farmstand as fs


@pytest.fixture
def inv():
    inv = fs.Inventory()
    inv.add_product("BAN", "Banana", 25, 40)
    inv.add_product("HNY", "Honey Jar", 850, 6)
    inv.add_product("EGG", "Dozen Eggs", 600, 2)
    return inv


@pytest.fixture
def cart(inv):
    return fs.Cart(inv)


# ---------------------------------------------------------------- lines

def test_new_cart_is_empty(cart):
    assert cart.lines() == []
    assert cart.count() == 0
    assert cart.subtotal() == 0
    assert cart.coupons() == []
    assert cart.discount_breakdown() == []
    assert cart.discount() == 0
    assert cart.totals() == {"subtotal": 0, "discount": 0, "tax": 0, "total": 0}


def test_add_and_lines(cart):
    cart.add("ban", 3)
    cart.add("HNY")
    assert cart.lines() == [("BAN", 3), ("HNY", 1)]


def test_adding_again_grows_the_line_in_place(cart):
    cart.add("BAN", 3)
    cart.add("HNY")
    cart.add(" ban ", 2)
    assert cart.lines() == [("BAN", 5), ("HNY", 1)]


def test_count_and_subtotal(cart):
    cart.add("BAN", 4)
    cart.add("HNY", 2)
    cart.add("EGG")
    assert cart.count() == 7
    assert cart.subtotal() == 2400


def test_subtotal_uses_current_prices(inv, cart):
    cart.add("HNY", 2)
    inv.set_price("HNY", 900)
    assert cart.subtotal() == 1800


@pytest.mark.parametrize("qty", [0, -1, 1.5, "2"])
def test_add_bad_qty(cart, qty):
    with pytest.raises(ValueError):
        cart.add("BAN", qty)
    assert cart.lines() == []


def test_add_unknown_sku(cart):
    with pytest.raises(fs.UnknownSkuError):
        cart.add("NOPE")


def test_add_more_than_stock(cart):
    with pytest.raises(fs.OutOfStockError):
        cart.add("EGG", 3)
    assert cart.lines() == []


def test_stock_limit_includes_what_is_already_in_the_cart(cart):
    cart.add("EGG", 2)
    with pytest.raises(fs.OutOfStockError):
        cart.add("egg")
    assert cart.lines() == [("EGG", 2)]


def test_add_does_not_touch_stock(inv, cart):
    cart.add("EGG", 2)
    assert inv.stock("EGG") == 2


def test_remove_some(cart):
    cart.add("BAN", 5)
    cart.remove("ban", 2)
    assert cart.lines() == [("BAN", 3)]


def test_remove_whole_line(cart):
    cart.add("BAN", 5)
    cart.add("HNY")
    cart.remove("BAN")
    assert cart.lines() == [("HNY", 1)]


def test_remove_down_to_zero_drops_the_line(cart):
    cart.add("BAN", 5)
    cart.remove("BAN", 5)
    assert cart.lines() == []


def test_readded_line_goes_to_the_end(cart):
    cart.add("BAN")
    cart.add("HNY")
    cart.remove("BAN")
    cart.add("BAN")
    assert cart.lines() == [("HNY", 1), ("BAN", 1)]


@pytest.mark.parametrize("qty", [0, -1, 3])
def test_remove_bad_qty(cart, qty):
    cart.add("BAN", 2)
    with pytest.raises(ValueError):
        cart.remove("BAN", qty)
    assert cart.lines() == [("BAN", 2)]


def test_remove_sku_not_in_cart(cart):
    cart.add("BAN")
    with pytest.raises(fs.UnknownSkuError):
        cart.remove("HNY")      # in the inventory, but not in the cart
    with pytest.raises(fs.UnknownSkuError):
        cart.remove("NOPE")


def test_clear(cart):
    cart.add("BAN", 2)
    cart.apply_coupon("SAVE10")
    cart.clear()
    assert cart.lines() == []
    assert cart.coupons() == []


# ---------------------------------------------------------------- coupons

def test_apply_coupon_returns_normalized_code(cart):
    assert cart.apply_coupon("  save10 ") == "SAVE10"
    assert cart.apply_coupon("bogo-hny") == "BOGO-HNY"


def test_save_coupon(cart):
    cart.add("BAN", 40)
    cart.apply_coupon("SAVE10")
    assert cart.discount_breakdown() == [("SAVE10", 100)]
    assert cart.discount() == 100


def test_save_coupon_rounds_half_up(cart):
    cart.add("HNY")
    cart.add("BAN")
    cart.apply_coupon("SAVE10")     # 10% of 875 = 87.5
    assert cart.discount() == 88


def test_minus_coupon(cart):
    cart.add("HNY", 2)
    cart.apply_coupon("minus500")
    assert cart.discount_breakdown() == [("MINUS500", 500)]


def test_minus_coupon_never_goes_below_zero(cart):
    cart.add("BAN", 2)
    cart.apply_coupon("MINUS500")
    assert cart.discount_breakdown() == [("MINUS500", 50)]
    assert cart.totals("9.125")["total"] == 0


@pytest.mark.parametrize("honey, free", [(1, 0), (2, 850), (3, 850), (4, 1700), (5, 1700), (6, 2550)])
def test_bogo_coupon(cart, honey, free):
    cart.add("HNY", honey)
    cart.add("BAN")
    cart.apply_coupon("BOGO-HNY")
    assert cart.discount_breakdown() == [("BOGO-HNY", free)]


def test_bogo_for_something_not_in_the_cart_is_worth_zero(cart):
    cart.add("BAN", 2)
    cart.apply_coupon("bogo-hny")
    assert cart.coupons() == ["BOGO-HNY"]
    assert cart.discount_breakdown() == [("BOGO-HNY", 0)]
    assert cart.discount() == 0


def test_bogo_counts_items_added_after_the_coupon(cart):
    cart.apply_coupon("BOGO-HNY")
    cart.add("HNY", 2)
    assert cart.discount() == 850


@pytest.mark.parametrize("code", ["SAVE1", "SAVE50", "MINUS1", "MINUS10000", "BOGO-EGG"])
def test_boundary_coupons_are_valid(cart, code):
    assert cart.apply_coupon(code) == code


@pytest.mark.parametrize("code", [
    "SAVE0", "SAVE51", "SAVE05", "SAVE", "SAVE10X", "SAVE-10", "SAVE 10",
    "MINUS0", "MINUS10001", "MINUS050", "MINUS",
    "BOGO-", "BOGO-NOPE", "BOGOHNY",
    "FREESTUFF", "",
])
def test_invalid_coupons(cart, code):
    with pytest.raises(fs.InvalidCouponError):
        cart.apply_coupon(code)
    assert cart.coupons() == []


def test_invalid_coupon_keeps_existing_coupons(cart):
    cart.apply_coupon("SAVE10")
    with pytest.raises(fs.InvalidCouponError):
        cart.apply_coupon("SAVE99")
    assert cart.coupons() == ["SAVE10"]


def test_same_kind_replaces(cart):
    cart.apply_coupon("SAVE10")
    cart.apply_coupon("SAVE20")
    cart.apply_coupon("BOGO-BAN")
    cart.apply_coupon("BOGO-HNY")
    cart.apply_coupon("MINUS100")
    cart.apply_coupon("MINUS200")
    assert cart.coupons() == ["BOGO-HNY", "SAVE20", "MINUS200"]


def test_coupons_are_listed_in_evaluation_order(cart):
    for code in ["MINUS300", "SAVE15", "BOGO-HNY"]:
        cart.apply_coupon(code)
    assert cart.coupons() == ["BOGO-HNY", "SAVE15", "MINUS300"]


def test_stacked_discount_math(cart):
    # The example from spec section 4.
    cart.add("BAN", 4)
    cart.add("HNY", 2)
    cart.add("EGG")
    for code in ["MINUS300", "SAVE15", "BOGO-HNY"]:
        cart.apply_coupon(code)
    assert cart.discount_breakdown() == [("BOGO-HNY", 850), ("SAVE15", 233), ("MINUS300", 300)]
    assert cart.discount() == 1383
    assert cart.totals("8.25") == {"subtotal": 2400, "discount": 1383, "tax": 84, "total": 1101}


def test_save_then_minus_can_reach_zero(cart):
    cart.add("EGG")
    cart.apply_coupon("MINUS10000")
    cart.apply_coupon("SAVE50")
    assert cart.discount_breakdown() == [("SAVE50", 300), ("MINUS10000", 300)]
    assert cart.totals("9.125") == {"subtotal": 600, "discount": 600, "tax": 0, "total": 0}


# ---------------------------------------------------------------- tax & totals

def test_totals_default_to_no_tax(cart):
    cart.add("BAN", 40)
    assert cart.totals() == {"subtotal": 1000, "discount": 0, "tax": 0, "total": 1000}


@pytest.mark.parametrize("tax, expected_tax", [
    (9, 90),
    ("8.25", 83),              # 82.5 rounds up
    (Decimal("9.125"), 91),    # 91.25
])
def test_totals_with_tax(cart, tax, expected_tax):
    cart.add("BAN", 40)
    totals = cart.totals(tax)
    assert totals == {"subtotal": 1000, "discount": 0, "tax": expected_tax,
                      "total": 1000 + expected_tax}
    assert all(type(v) is int for v in totals.values())


def test_tax_applies_after_discounts(cart):
    cart.add("BAN", 40)
    cart.apply_coupon("MINUS200")
    assert cart.totals("8.25") == {"subtotal": 1000, "discount": 200, "tax": 66, "total": 866}

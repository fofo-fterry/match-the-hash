"""Spec sections 5 and 6: the Stand, checkout, and receipts."""
import pytest

import farmstand as fs

EXAMPLE_RECEIPT = """\
CARDINAL FARMS
Sale #1                       2026-10-20
----------------------------------------
3 x Banana                         $0.75
3 x Honey Jar                     $25.50
1 x Dozen Eggs                     $6.00
----------------------------------------
Subtotal                          $32.25
BOGO-HNY                          -$8.50
SAVE10                            -$2.38
Tax                                $1.95
TOTAL                             $23.32"""


@pytest.fixture
def stand():
    stand = fs.Stand("Cardinal Farms")
    stand.inventory.add_product("BAN", "Banana", 25, 40)
    stand.inventory.add_product("HNY", "Honey Jar", 850, 6)
    stand.inventory.add_product("EGG", "Dozen Eggs", 600, 12)
    return stand


def example_sale(stand):
    """The worked example from the README."""
    cart = stand.new_cart()
    cart.add("ban", 3)
    cart.add("HNY", 3)
    cart.add("EGG")
    cart.apply_coupon("save10")
    cart.apply_coupon("bogo-hny")
    return stand.checkout(cart, "2026-10-20", tax_percent="9.125")


def quick_sale(stand, sku="BAN", qty=1, day="2026-10-20"):
    cart = stand.new_cart()
    cart.add(sku, qty)
    return stand.checkout(cart, day)


# ---------------------------------------------------------------- stand

def test_stand_name_is_stripped():
    assert fs.Stand("  Cardinal Farms ").name == "Cardinal Farms"


@pytest.mark.parametrize("name", ["", "   ", None])
def test_bad_stand_name(name):
    with pytest.raises(ValueError):
        fs.Stand(name)


def test_new_stand_has_an_empty_inventory():
    stand = fs.Stand("Cardinal Farms")
    assert isinstance(stand.inventory, fs.Inventory)
    assert len(stand.inventory) == 0


def test_new_cart_uses_the_stand_inventory(stand):
    cart = stand.new_cart()
    assert isinstance(cart, fs.Cart)
    cart.add("BAN", 2)
    assert cart.subtotal() == 50


# ---------------------------------------------------------------- checkout

def test_checkout_returns_a_sale(stand):
    sale = example_sale(stand)
    assert sale.number == 1
    assert sale.day == "2026-10-20"
    assert sale.lines == [("BAN", "Banana", 3, 25),
                          ("HNY", "Honey Jar", 3, 850),
                          ("EGG", "Dozen Eggs", 1, 600)]
    assert sale.discounts == [("BOGO-HNY", 850), ("SAVE10", 238)]
    assert (sale.subtotal, sale.discount, sale.tax, sale.total) == (3225, 1088, 195, 2332)
    assert sale.refunded is False


def test_checkout_takes_units_out_of_stock(stand):
    example_sale(stand)
    inv = stand.inventory
    assert (inv.stock("BAN"), inv.stock("HNY"), inv.stock("EGG")) == (37, 3, 11)


def test_checkout_empties_the_cart(stand):
    cart = stand.new_cart()
    cart.add("BAN", 2)
    cart.apply_coupon("SAVE10")
    stand.checkout(cart, "2026-10-20")
    assert cart.lines() == []
    assert cart.coupons() == []


def test_sale_numbers_count_up(stand):
    numbers = [quick_sale(stand).number for _ in range(3)]
    assert numbers == [1, 2, 3]


def test_tax_defaults_to_zero(stand):
    sale = quick_sale(stand, "HNY", 2)
    assert (sale.subtotal, sale.discount, sale.tax, sale.total) == (1700, 0, 0, 1700)


def test_leap_day_is_a_real_date(stand):
    assert quick_sale(stand, day="2024-02-29").day == "2024-02-29"


def test_empty_cart_cannot_check_out(stand):
    with pytest.raises(ValueError):
        stand.checkout(stand.new_cart(), "2026-10-20")


@pytest.mark.parametrize("day", [
    "2026-13-01", "2026-02-30", "2025-02-29", "2026-1-05", "10/20/2026",
    "20261020", "2026-10-20T09:00", "", "yesterday", None,
])
def test_bad_day_changes_nothing(stand, day):
    cart = stand.new_cart()
    cart.add("BAN", 2)
    with pytest.raises(ValueError):
        stand.checkout(cart, day)
    assert stand.inventory.stock("BAN") == 40
    assert cart.lines() == [("BAN", 2)]
    assert quick_sale(stand).number == 1


def test_out_of_stock_at_checkout_changes_nothing(stand):
    first = stand.new_cart()
    first.add("EGG", 10)
    second = stand.new_cart()
    second.add("BAN", 1)
    second.add("EGG", 5)
    second.apply_coupon("SAVE10")

    stand.checkout(first, "2026-10-20")     # only 2 eggs left now
    with pytest.raises(fs.OutOfStockError):
        stand.checkout(second, "2026-10-20")
    assert stand.inventory.stock("EGG") == 2
    assert stand.inventory.stock("BAN") == 40
    assert second.lines() == [("BAN", 1), ("EGG", 5)]
    assert second.coupons() == ["SAVE10"]

    stand.inventory.restock("EGG", 3)
    assert stand.checkout(second, "2026-10-21").number == 2


def test_sale_keeps_the_price_from_checkout_time(stand):
    sale = quick_sale(stand, "HNY", 1)
    stand.inventory.set_price("HNY", 999)
    assert sale.lines == [("HNY", "Honey Jar", 1, 850)]
    assert sale.total == 850
    assert "$8.50" in sale.receipt()


# ---------------------------------------------------------------- receipts

def test_receipt_matches_the_spec_example(stand):
    assert example_sale(stand).receipt() == EXAMPLE_RECEIPT


def test_receipt_rows_are_40_wide(stand):
    receipt = example_sale(stand).receipt()
    assert not receipt.endswith("\n")
    assert all(len(line) == 40 for line in receipt.split("\n")[1:])


def test_receipt_leaves_out_coupons_worth_zero(stand):
    cart = stand.new_cart()
    cart.add("BAN", 8)
    cart.apply_coupon("BOGO-HNY")   # no honey in the cart: worth 0
    cart.apply_coupon("MINUS10")
    sale = stand.checkout(cart, "2026-10-20")
    assert sale.discounts == [("BOGO-HNY", 0), ("MINUS10", 10)]
    assert sale.receipt() == "\n".join([
        "CARDINAL FARMS",
        "Sale #1                       2026-10-20",
        "-" * 40,
        "8 x Banana                         $2.00",
        "-" * 40,
        "Subtotal                           $2.00",
        "MINUS10                           -$0.10",
        "Tax                                $0.00",
        "TOTAL                              $1.90",
    ])


def test_receipt_row_that_does_not_fit_uses_one_space():
    stand = fs.Stand("The Long Name Stand")
    stand.inventory.add_product("LOAF", "Extra Large Heirloom Pumpkin Spice Loaf", 1200, 1)
    sale = quick_sale(stand, "LOAF", 1, "2026-10-31")
    lines = sale.receipt().split("\n")
    assert lines[0] == "THE LONG NAME STAND"
    assert lines[3] == "1 x Extra Large Heirloom Pumpkin Spice Loaf $12.00"


def test_receipt_shows_big_numbers_with_commas():
    stand = fs.Stand("Tractor Barn")
    stand.inventory.add_product("TRACTOR", "Tractor", 1250000, 2)
    sale = quick_sale(stand, "TRACTOR", 2, "2026-11-01")
    lines = sale.receipt().split("\n")
    assert lines[1] == "Sale #1                       2026-11-01"
    assert lines[3] == "2 x Tractor                   $25,000.00"
    assert lines[-1] == "TOTAL                         $25,000.00"

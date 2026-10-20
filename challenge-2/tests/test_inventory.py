"""Spec sections 2 and 3: the error classes and the Inventory."""
import pytest

import farmstand as fs


@pytest.fixture
def inv():
    inv = fs.Inventory()
    inv.add_product("BAN", "Banana", 25, 40)
    inv.add_product("HNY", "Honey Jar", 850, 6)
    inv.add_product("EGG", "Dozen Eggs", 600, 2)
    return inv


def test_error_classes():
    assert issubclass(fs.FarmStandError, Exception)
    for name in ["UnknownSkuError", "DuplicateSkuError", "OutOfStockError",
                 "InvalidCouponError", "UnknownSaleError", "AlreadyRefundedError"]:
        assert issubclass(getattr(fs, name), fs.FarmStandError), name
    assert issubclass(fs.UnknownSkuError, KeyError)
    assert issubclass(fs.UnknownSaleError, KeyError)
    assert issubclass(fs.DuplicateSkuError, ValueError)
    assert issubclass(fs.InvalidCouponError, ValueError)


def test_add_product_returns_the_product():
    p = fs.Inventory().add_product("BAN", "Banana", 25, 40)
    assert (p.sku, p.name, p.price, p.qty) == ("BAN", "Banana", 25, 40)


def test_get(inv):
    p = inv.get("HNY")
    assert (p.sku, p.name, p.price, p.qty) == ("HNY", "Honey Jar", 850, 6)


def test_qty_defaults_to_zero():
    inv = fs.Inventory()
    inv.add_product("PIE", "Apple Pie", 1800)
    assert inv.stock("PIE") == 0


def test_free_items_are_allowed():
    p = fs.Inventory().add_product("SAMPLE", "Free Sample", 0, 100)
    assert p.price == 0


def test_sku_is_normalized():
    inv = fs.Inventory()
    p = inv.add_product("  tom-1 ", "Tomato", 125, 3)
    assert p.sku == "TOM-1"
    assert inv.get("tom-1").sku == "TOM-1"
    assert inv.stock(" Tom-1") == 3


@pytest.mark.parametrize("sku", ["A", "7", "1-2", "ABCDEFGHIJKL"])
def test_sku_edge_cases_accepted(sku):
    inv = fs.Inventory()
    inv.add_product(sku, "Thing", 100)
    assert sku in inv


@pytest.mark.parametrize("sku", ["", "   ", "TWO WORDS", "BAD!", "A_B", "ABCDEFGHIJKLM", "CAFÉ"])
def test_bad_sku_rejected(sku):
    inv = fs.Inventory()
    with pytest.raises(ValueError):
        inv.add_product(sku, "Thing", 100)
    assert len(inv) == 0


def test_name_is_stripped():
    p = fs.Inventory().add_product("CORN", "  Sweet Corn  ", 80, 5)
    assert p.name == "Sweet Corn"


@pytest.mark.parametrize("name", ["", "    ", None])
def test_bad_name_rejected(name):
    with pytest.raises(ValueError):
        fs.Inventory().add_product("X", name, 100)


@pytest.mark.parametrize("price", [-1, 3.5, "350", None])
def test_bad_price_rejected(price):
    with pytest.raises(ValueError):
        fs.Inventory().add_product("X", "Thing", price)


@pytest.mark.parametrize("qty", [-1, 2.0, "5"])
def test_bad_qty_rejected(qty):
    with pytest.raises(ValueError):
        fs.Inventory().add_product("X", "Thing", 100, qty)


def test_duplicate_sku_rejected(inv):
    with pytest.raises(fs.DuplicateSkuError):
        inv.add_product(" ban", "Plantain", 30)
    assert inv.get("BAN").name == "Banana"
    assert len(inv) == 3


def test_unknown_sku(inv):
    with pytest.raises(fs.UnknownSkuError):
        inv.get("NOPE")
    with pytest.raises(fs.UnknownSkuError):
        inv.stock("NOPE")
    with pytest.raises(fs.UnknownSkuError):
        inv.restock("NOPE", 5)
    with pytest.raises(fs.UnknownSkuError):
        inv.set_price("NOPE", 100)
    with pytest.raises(KeyError):
        inv.get("NOPE")


def test_restock(inv):
    assert inv.restock("egg", 10) == 12
    assert inv.stock("EGG") == 12


@pytest.mark.parametrize("qty", [0, -3, 1.5])
def test_restock_bad_qty(inv, qty):
    with pytest.raises(ValueError):
        inv.restock("EGG", qty)
    assert inv.stock("EGG") == 2


def test_set_price(inv):
    inv.set_price("hny", 900)
    assert inv.get("HNY").price == 900


@pytest.mark.parametrize("price", [-5, 9.99, "900"])
def test_set_price_bad_price(inv, price):
    with pytest.raises(ValueError):
        inv.set_price("HNY", price)
    assert inv.get("HNY").price == 850


def test_skus_sorted(inv):
    assert inv.skus() == ["BAN", "EGG", "HNY"]


def test_low_stock_default_threshold(inv):
    assert inv.low_stock() == ["EGG"]
    inv.add_product("PIE", "Apple Pie", 1800, 5)   # exactly at the threshold counts
    inv.add_product("JAM", "Jam", 375, 2)          # ties with EGG -> SKU order
    assert inv.low_stock() == ["EGG", "JAM", "PIE"]


def test_low_stock_custom_threshold(inv):
    assert inv.low_stock(6) == ["EGG", "HNY"]
    assert inv.low_stock(100) == ["EGG", "HNY", "BAN"]
    assert inv.low_stock(1) == []


def test_len_and_contains(inv):
    assert len(fs.Inventory()) == 0
    assert len(inv) == 3
    assert "ban" in inv
    assert " Hny " in inv
    assert "PIE" not in inv
    assert "not a sku!" not in inv

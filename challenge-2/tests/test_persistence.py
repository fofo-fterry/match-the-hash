"""Spec section 8: saving and loading."""
import pytest

import farmstand as fs


@pytest.fixture
def stand():
    stand = fs.Stand("Cardinal Farms")
    inv = stand.inventory
    inv.add_product("BAN", "Banana", 25, 40)
    inv.add_product("HNY", "Honey Jar", 850, 6)
    inv.add_product("PIE", "Apple Pie", 1800, 0)    # sold out but still listed

    for day, items, coupons in [
        ("2026-10-18", [("BAN", 4), ("HNY", 3)], ["BOGO-HNY", "SAVE10"]),
        ("2026-10-19", [("HNY", 1)], ["MINUS100"]),
        ("2026-10-19", [("BAN", 10)], []),
    ]:
        cart = stand.new_cart()
        for sku, qty in items:
            cart.add(sku, qty)
        for code in coupons:
            cart.apply_coupon(code)
        stand.checkout(cart, day, "9.125")
    stand.refund(2)
    return stand


@pytest.fixture
def loaded(stand, tmp_path):
    path = tmp_path / "stand.dat"
    stand.save(path)
    return fs.Stand.load(path)


def sale_fields(sale):
    return (sale.number, sale.day, sale.lines, sale.discounts, sale.subtotal,
            sale.discount, sale.tax, sale.total, sale.refunded)


def test_save_creates_a_file(stand, tmp_path):
    path = tmp_path / "stand.dat"
    stand.save(path)
    assert path.exists()


def test_paths_can_be_strings(stand, tmp_path):
    path = str(tmp_path / "stand.dat")
    stand.save(path)
    assert fs.Stand.load(path).name == "Cardinal Farms"


def test_load_returns_a_stand(loaded):
    assert isinstance(loaded, fs.Stand)
    assert loaded.name == "Cardinal Farms"


def test_products_survive(stand, loaded):
    assert loaded.inventory.skus() == ["BAN", "HNY", "PIE"]
    for sku in stand.inventory.skus():
        before, after = stand.inventory.get(sku), loaded.inventory.get(sku)
        assert (after.sku, after.name, after.price, after.qty) == \
               (before.sku, before.name, before.price, before.qty)


def test_sales_survive(stand, loaded):
    assert [sale_fields(s) for s in loaded.sales()] == [sale_fields(s) for s in stand.sales()]
    assert loaded.sale(2).refunded is True


def test_sale_lines_are_still_tuples(loaded):
    sale = loaded.sale(1)
    assert sale.lines == [("BAN", "Banana", 4, 25), ("HNY", "Honey Jar", 3, 850)]
    assert all(type(line) is tuple for line in sale.lines)
    assert all(type(d) is tuple for d in sale.discounts)


def test_receipts_survive(stand, loaded):
    for before, after in zip(stand.sales(), loaded.sales()):
        assert after.receipt() == before.receipt()


def test_reports_survive(stand, loaded):
    assert loaded.revenue() == stand.revenue()
    assert loaded.units_sold() == stand.units_sold()
    assert loaded.top_sellers() == stand.top_sellers()
    assert loaded.daily_summary() == stand.daily_summary()


def test_numbering_continues_after_load(loaded):
    cart = loaded.new_cart()
    cart.add("ban")
    sale = loaded.checkout(cart, "2026-10-20")
    assert sale.number == 4
    assert loaded.inventory.stock("BAN") == 25


def test_refunds_work_after_load(loaded):
    with pytest.raises(fs.AlreadyRefundedError):
        loaded.refund(2)
    loaded.refund(3)
    assert loaded.inventory.stock("BAN") == 36


def test_save_overwrites(stand, tmp_path):
    path = tmp_path / "stand.dat"
    stand.save(path)
    stand.inventory.restock("PIE", 4)
    stand.save(path)
    assert fs.Stand.load(path).inventory.stock("PIE") == 4


def test_load_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        fs.Stand.load(tmp_path / "nope.dat")

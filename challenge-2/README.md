# Challenge 2: The Farm Stand

Cardinal Farms sells produce, honey, and T-shirts from a stand at the edge of
campus. Right now their point of sale is a shoebox full of receipts. Your job
is to build the software they need: a small Python module called `farmstand`,
written to the spec below.

The spec is the contract and the unit tests in `tests/` enforce it. When
**every** test passes, the test run prints a **passphrase**. Say it out loud to
your team.

## What you get

```
challenge-2/
├── README.md      <- this spec
└── tests/         <- the unit tests (read them all you like, don't edit them)
```

You add one file, `challenge-2/farmstand.py`. A `farmstand/` package works
too.

## Running the tests

You need Python 3.9 or newer and pytest. The standard library covers
everything else.

```bash
cd challenge-2
python -m pip install pytest
python -m pytest                        # the whole suite
python -m pytest tests/test_money.py    # one section at a time
```

Every run ends with a progress line, for example
`41/224 tests passing. Passphrase still locked.` Once they all pass you get
the passphrase banner.

### Why editing the tests won't help

The passphrase is encrypted, and the key is built from what *your* `farmstand`
returns in `tests/test_sealed.py`. Those tests show their inputs, but the
correct answers appear only as SHA-256 fingerprints. Only an app that follows
the spec can produce the key. Delete an assertion and the banner simply never
appears.

When the regular tests pass and a sealed test fails, its message tells you
which spec sections to reread.

## Rules

1. Use any tools you like: AI assistants, docs, search engines, teammates.
2. Leave `tests/` alone.
3. Got the passphrase? Share it verbally with your team. Don't paste it into a
   chat.

Stuck? The organizers have hints.

---

# The spec

| Section | Tests |
|---|---|
| [0. Ground rules](#0-ground-rules) | (everywhere) |
| [1. Money helpers](#1-money-helpers) | `test_money.py` |
| [2. Errors](#2-errors) | `test_inventory.py` |
| [3. Inventory](#3-inventory) | `test_inventory.py` |
| [4. Cart and coupons](#4-cart-and-coupons) | `test_cart.py` |
| [5. The stand and checkout](#5-the-stand-and-checkout) | `test_checkout.py` |
| [6. Receipts](#6-receipts) | `test_checkout.py` |
| [7. Refunds and reports](#7-refunds-and-reports) | `test_reports.py` |
| [8. Saving and loading](#8-saving-and-loading) | `test_persistence.py` |
| [Worked example](#worked-example) | |
| All of the above, end to end | `test_sealed.py` |

## 0. Ground rules

- **Money is always an integer number of cents.** `350` means $3.50. Every
  money value you return is an `int`, never a `float` or a `Decimal`.
- **Percentages** (coupon percents and tax rates) arrive as an `int` (`10`), a
  numeric string (`"9.125"`), or a `decimal.Decimal`. You don't need to
  support floats.
- **Rounding:** if a calculation produces a fraction of a cent, round to the
  nearest cent, with **halves rounding up** (`82.5` becomes `83`). Python's
  built-in `round()` rounds halves to the even neighbor (`round(82.5) == 82`),
  so it's the wrong tool here.
- **SKUs** (product codes) ignore case. Every method that takes a SKU first
  strips the surrounding whitespace and uppercases it, so `" ban "`, `"ban"`,
  and `"BAN"` all refer to the same product. SKUs are always returned in
  uppercase.
- When the spec says "raises `X`", it means raise that exception class or a
  subclass of it.

## 1. Money helpers

Three module-level functions.

### `parse_price(text) -> int`

This turns a price string into cents. First strip the whitespace from both
ends. What's left must be exactly these parts, in this order:

1. an optional `$`
2. the dollars, in one of two forms:
   - plain digits, such as `1234`
   - digits grouped in threes with commas, such as `1,234` or `12,345,678`.
     The first group has 1 to 3 digits and every group after it has exactly
     3.
3. optionally, a `.` followed by **one or two** digits of cents. A single
   digit counts as tens of cents, so `"3.5"` is `350`.

Any other input raises `ValueError`.

| Input | Result |
|---|---|
| `"3"` | `300` |
| `"3.5"` | `350` |
| `"$3.50"` | `350` |
| `"  $12.00 "` | `1200` |
| `"$1,234.56"` | `123456` |
| `""`, `"$"`, `"3."`, `".50"`, `"3.505"`, `"-1"`, `"1,00"`, `"$ 3"`, `"3$"` | `ValueError` |

### `format_price(cents) -> str`

This turns cents into a display string: `$`, then the dollars with commas
between thousands, then `.` and exactly two digits of cents. A negative amount
gets a minus sign in front of the `$`.

| Input | Result |
|---|---|
| `0` | `"$0.00"` |
| `5` | `"$0.05"` |
| `123456` | `"$1,234.56"` |
| `-250` | `"-$2.50"` |

### `percent_of(cents, percent) -> int`

This returns `cents × percent ÷ 100`, rounded half up to a whole cent.
`cents` is an `int` of 0 or more, and `percent` is 0 or more.

| Call | Result |
|---|---|
| `percent_of(1000, 10)` | `100` |
| `percent_of(1000, "8.25")` | `83` (82.5 rounds up) |
| `percent_of(1050, "9.125")` | `96` (95.8125) |

## 2. Errors

Define these exception classes in `farmstand`:

| Class | Inherits from | Raised when |
|---|---|---|
| `FarmStandError` | `Exception` | (base class for all the others) |
| `UnknownSkuError` | `FarmStandError`, `KeyError` | a SKU isn't in the inventory, or (for `Cart.remove`) isn't in the cart |
| `DuplicateSkuError` | `FarmStandError`, `ValueError` | you add a SKU that already exists |
| `OutOfStockError` | `FarmStandError` | there isn't enough stock |
| `InvalidCouponError` | `FarmStandError`, `ValueError` | a coupon code isn't valid |
| `UnknownSaleError` | `FarmStandError`, `KeyError` | no sale has that number |
| `AlreadyRefundedError` | `FarmStandError` | a sale is refunded a second time |

Bad argument values, such as a negative price, a zero quantity, or a
malformed date, raise a plain `ValueError`.

## 3. Inventory

`Inventory()` creates an empty inventory. Each product has four attributes:
`sku`, `name`, `price` (in cents), and `qty` (the units in stock). Products are
returned as objects with those four attributes. A dataclass is a good fit.

**SKU format.** `add_product` is the only method that checks it. After
stripping and uppercasing, a SKU is 1 to 12 characters long, and each
character is an ASCII letter `A`–`Z`, a digit `0`–`9`, or `-`.

| Method | Behavior |
|---|---|
| `add_product(sku, name, price, qty=0)` | Adds a product and returns it. Raises `ValueError` if the SKU format is bad, if `name` isn't a string or is empty after stripping (store it stripped), if `price` isn't an `int` of 0 or more, or if `qty` isn't an `int` of 0 or more. Raises `DuplicateSkuError` if the SKU already exists. |
| `get(sku)` | Returns the product. |
| `stock(sku)` | Returns the product's `qty`. |
| `restock(sku, qty)` | Adds `qty` units and returns the new stock level. `qty` must be an `int` of 1 or more, otherwise `ValueError`. |
| `set_price(sku, price)` | Changes the price. `price` must be an `int` of 0 or more, otherwise `ValueError`. |
| `skus()` | Returns a list of every SKU, sorted A→Z. |
| `low_stock(threshold=5)` | Returns the SKUs whose `qty` is **at or below** `threshold`, lowest `qty` first, ties broken by SKU A→Z. |
| `len(inventory)` | Returns the number of products. |
| `sku in inventory` | `True` if that SKU exists, case-insensitive. Never raises. |

`get`, `stock`, `restock`, and `set_price` raise `UnknownSkuError` for a SKU
that isn't in the inventory.

## 4. Cart and coupons

`Cart(inventory)` creates an empty cart. The cart reads products, prices, and
stock from that inventory at the moment you ask, so its totals always use the
**current** prices. Putting something in a cart doesn't change stock. Only
checkout does that.

| Method | Behavior |
|---|---|
| `add(sku, qty=1)` | Adds units. `qty` must be an `int` of 1 or more, otherwise `ValueError`. Raises `UnknownSkuError` for an unknown SKU. If the cart would end up holding more of that SKU than is in stock, raises `OutOfStockError` and leaves the cart unchanged. Adding more of a SKU that's already in the cart increases that line's quantity and keeps the line where it is. |
| `remove(sku, qty=None)` | With `qty=None`, removes the whole line. Otherwise `qty` must be an `int` from 1 up to the quantity in the cart, else `ValueError`. A line whose quantity reaches 0 disappears. A SKU that isn't in the cart raises `UnknownSkuError`. |
| `lines()` | Returns a list of `(sku, qty)` tuples in the order each SKU was first added. A SKU that's removed completely and then added again goes to the end. |
| `count()` | Returns the total number of units in the cart. |
| `subtotal()` | Returns the sum of price × qty over all lines. |
| `apply_coupon(code)` | Checks a coupon and applies it (see below). Returns the normalized code. |
| `coupons()` | Returns the applied coupon codes, normalized, in **evaluation order**: BOGO, then SAVE, then MINUS. |
| `discount_breakdown()` | Returns a list of `(code, amount)` tuples, one per applied coupon, in evaluation order. Coupons worth 0 are included. |
| `discount()` | Returns the total discount, which is the sum of the breakdown amounts. |
| `totals(tax_percent=0)` | Returns a dict with exactly the keys `"subtotal"`, `"discount"`, `"tax"`, and `"total"`. |
| `clear()` | Removes every line and every coupon. |

For an empty cart, every number above is 0.

### Coupon codes

`apply_coupon` strips the whitespace from the code and uppercases it. The
result is the **normalized code**. There are three kinds of coupon:

| Kind | Pattern | Valid when | Discount |
|---|---|---|---|
| SAVE | `SAVE<N>` | `N` is a whole number from 1 to 50 with no leading zeros | `N` percent off |
| MINUS | `MINUS<C>` | `C` is a whole number of cents from 1 to 10000 with no leading zeros | `C` cents off |
| BOGO | `BOGO-<SKU>` | `<SKU>` is a product in the inventory | buy one, get one free on that SKU |

Any other code raises `InvalidCouponError` and leaves the cart's coupons as
they were. Some invalid codes: `SAVE0`, `SAVE51`, `SAVE05`, `MINUS`,
`BOGO-NOPE` (no product with that SKU), and `FREESTUFF`.

A BOGO coupon for a SKU that isn't in the cart is still valid. It's just
worth 0 until that SKU is added.

A cart holds **at most one coupon of each kind**, so applying a second coupon
of the same kind replaces the first. That gives a cart at most three coupons:
one BOGO, one SAVE, and one MINUS.

### Discount math

Coupons are always evaluated in the same order, whatever order they were
applied in. Each step works on what's left after the steps before it:

1. **BOGO** on SKU `S`: every second unit of `S` is free.
   `bogo = (units of S in the cart // 2) × price of S`
2. **SAVE N**: `save = percent_of(subtotal − bogo, N)`
3. **MINUS C**: `minus = min(C, subtotal − bogo − save)`, which keeps the
   total from going below zero.

A coupon that isn't applied counts as 0, and
`discount = bogo + save + minus`.

### Tax and total

```
tax   = percent_of(subtotal − discount, tax_percent)
total = subtotal − discount + tax
```

Take this cart: 4 bananas at 25¢, 2 honey jars at $8.50, and 1 dozen eggs at
$6.00. The coupons are applied in the order `MINUS300`, `SAVE15`, `BOGO-HNY`,
and tax is `"8.25"`:

| Step | Math | Amount |
|---|---|---|
| subtotal | 100 + 1700 + 600 | 2400 |
| BOGO-HNY | (2 // 2) × 850 | 850 |
| SAVE15 | 15% of (2400 − 850) = 232.5, rounds up | 233 |
| MINUS300 | min(300, 2400 − 850 − 233) | 300 |
| discount | 850 + 233 + 300 | 1383 |
| tax | 8.25% of (2400 − 1383) = 83.9025 | 84 |
| total | 2400 − 1383 + 84 | 1101 |

`coupons()` returns `["BOGO-HNY", "SAVE15", "MINUS300"]`.

## 5. The stand and checkout

`Stand(name)` creates a stand. `name` must be a string that isn't empty after
stripping, otherwise `ValueError`. Store it stripped. A stand has:

- `stand.name`
- `stand.inventory`, its own `Inventory`, which starts out empty
- `stand.new_cart()`, which returns a new empty `Cart` for this stand's
  inventory

### `stand.checkout(cart, day, tax_percent=0)`

This sells everything in the cart and returns a sale object (call the class
`Sale`).

1. `day` must be a real calendar date written exactly as `YYYY-MM-DD`: ten
   characters, such as `"2026-10-20"`. Anything else raises `ValueError`.
2. An empty cart raises `ValueError`.
3. If any line needs more units than are in stock right now, raise
   `OutOfStockError`. This happens when another cart bought them first.
4. Otherwise, record the sale using the current prices and the cart's
   coupons, take the units out of stock, empty the cart (both lines and
   coupons), and return the sale.

**When checkout raises, nothing changes.** Stock, the cart, and the sale
numbering all stay as they were.

At each stand, sale numbers start at 1 and go up by one with every checkout.
A number is never reused.

A sale has these attributes:

| Attribute | Type | Value |
|---|---|---|
| `number` | `int` | the sale number |
| `day` | `str` | the day passed to `checkout` |
| `lines` | list of tuples | one `(sku, name, qty, unit_price)` per cart line, in cart order, priced at checkout time |
| `discounts` | list of tuples | what `cart.discount_breakdown()` returned at checkout time |
| `subtotal`, `discount`, `tax`, `total` | `int` | what `cart.totals(tax_percent)` returned at checkout time |
| `refunded` | `bool` | `False` until the sale is refunded |

It also has one method, `receipt()`.

## 6. Receipts

`sale.receipt()` returns the receipt as a single string, built from these
pieces:

- A **row** is a left text and a right text with enough spaces between them
  to make the row exactly **40 characters** wide. There's always at least one
  space. If the two texts are too long for that, put exactly one space
  between them and let the row run longer than 40.
- A **rule** is 40 hyphens.
- Lines are joined with `"\n"`, with no newline at the very end.

The lines, from top to bottom:

1. The stand's name in uppercase.
2. A row with `Sale #<number>` on the left and the day on the right.
3. A rule.
4. One row per sale line, with `<qty> x <name>` on the left and
   `format_price(qty × unit_price)` on the right.
5. A rule.
6. A row with `Subtotal` and the subtotal.
7. One row per discount whose amount is **more than 0**, in evaluation order,
   with the code on the left and `format_price(-amount)` on the right.
   Coupons worth 0 are left off the receipt.
8. A row with `Tax` and the tax. This row always appears, even when the tax
   is `$0.00`.
9. A row with `TOTAL` and the total.
10. Only for a refunded sale: `*** REFUNDED ***`

The sale from the [worked example](#worked-example) prints this:

```
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
TOTAL                             $23.32
```

## 7. Refunds and reports

| Method | Behavior |
|---|---|
| `stand.sale(number)` | Returns the sale with that number. Raises `UnknownSaleError` if there's no such sale. |
| `stand.sales()` | Returns every sale, refunded ones included, lowest number first. |
| `stand.refund(number)` | Puts every unit from that sale back in stock, marks the sale refunded, and returns its `total`. Raises `UnknownSaleError` if there's no such sale and `AlreadyRefundedError` if it was already refunded. |

These reports **ignore refunded sales**:

| Method | Returns |
|---|---|
| `stand.revenue(day=None)` | The sum of sale totals, tax included. If `day` is given, only sales on that day count. Returns 0 when there are no matching sales. |
| `stand.units_sold()` | A dict of `{sku: units}` over all sales. SKUs that sold nothing are left out. |
| `stand.top_sellers(n=3)` | Up to `n` `(sku, units)` tuples, most units first, ties broken by SKU A→Z. |
| `stand.daily_summary()` | A list of `(day, number_of_sales, revenue)` tuples, earliest day first. Days with no sales left after refunds are omitted. |

## 8. Saving and loading

| Method | Behavior |
|---|---|
| `stand.save(path)` | Writes the whole stand to a file. `path` is a `str` or a `pathlib.Path`, and an existing file is overwritten. The file format is up to you; JSON is easy. |
| `Stand.load(path)` | A class method or static method that reads the file back into a new `Stand`. |

A loaded stand must behave exactly like the original:

- the same name
- the same products, with the same SKU, name, price, and qty
- the same sales, with every attribute equal. `lines` and `discounts` are
  still lists of **tuples**.
- identical receipts
- the next checkout gets the next sale number

Carts aren't saved. Loading a file that doesn't exist raises
`FileNotFoundError`.

---

## Worked example

```python
import farmstand as fs

stand = fs.Stand("Cardinal Farms")
inv = stand.inventory
inv.add_product("BAN", "Banana", 25, 40)
inv.add_product("hny", "Honey Jar", 850, 6)     # stored as "HNY"
inv.add_product("EGG", "Dozen Eggs", 600, 12)

cart = stand.new_cart()
cart.add("ban", 3)
cart.add("HNY", 3)
cart.add("EGG")
cart.apply_coupon("save10")                     # -> "SAVE10"
cart.apply_coupon("bogo-hny")                   # -> "BOGO-HNY"

cart.coupons()          # ["BOGO-HNY", "SAVE10"]   (evaluation order)
cart.totals("9.125")    # {"subtotal": 3225, "discount": 1088, "tax": 195, "total": 2332}

sale = stand.checkout(cart, "2026-10-20", tax_percent="9.125")
sale.number             # 1
sale.lines              # [("BAN", "Banana", 3, 25), ("HNY", "Honey Jar", 3, 850), ("EGG", "Dozen Eggs", 1, 600)]
sale.discounts          # [("BOGO-HNY", 850), ("SAVE10", 238)]
inv.stock("HNY")        # 3
cart.lines()            # []
stand.revenue()         # 2332
print(sale.receipt())   # the receipt shown in section 6
```

The math: the subtotal is 3·25 + 3·850 + 600 = 3225. BOGO makes 1 of the 3
honey jars free, so 850 off. SAVE10 is 10% of 2375, which is 237.5 and rounds
up to 238. That leaves 2137, and 9.125% tax on it is 195.00125, which rounds
to 195. The total is 2137 + 195 = 2332.

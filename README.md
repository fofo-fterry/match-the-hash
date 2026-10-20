# The Farm Hash Challenge (Research Edition)

Behind this hash is a secret phrase built from three pieces. One piece you
*research*, one piece you *research* (and it's trickier than it looks), and one
piece your *code* has to hunt down. You'll need your brain, the web, and a
script. An AI assistant can help you write the code, but it can't hand you the
answer.

## What you get

`challenge.json`:

```json
{
  "algorithm": "sha256",
  "format": "sha256(salt + secret), UTF-8, lowercase hex",
  "salt": "stanford-2026-yo:"
}
```

(The `hash` field is in the file.) You can't reverse a hash. You can only
assemble a candidate phrase, hash it the same way, and check for a match.

## How the secret is built

Three pieces, concatenated in order, **all lowercase, no spaces**:

```
secret = PIECE_1 + PIECE_2 + PIECE_3
```

### Piece 1 - research (a number)

The year Stanford **opened its doors to students**.

> Careful: the year the university was *founded/granted* and the year it
> *opened* are not the same. The hints want the one where students actually
> showed up. Look it up; don't guess.

### Piece 2 - research (a word)

The **last word of Stanford's official motto, written in its original
language** - not the English translation.

> You'll have to find the motto, notice what language it's in, and copy the
> final word exactly.

### Piece 3 - code (a word)

A common **6-letter English word**. Here's the only clue:

> The word's **own SHA-256 hash** (just the word, lowercase, no salt) begins
> with `8a62e`.

There is exactly one such word in a standard English wordlist. You'll have to
write a loop that hashes every 6-letter word and checks the prefix. No
shortcuts - this is the part that *requires* code.

## Your job

1. Research pieces 1 and 2.
2. Write code to find piece 3.
3. Concatenate them, compute `sha256(salt + secret)`, and confirm it equals the
   hash in `challenge.json`.

## Rules

1. Any tool is allowed: AI chatbots, wordlists, search engines, friends.
2. Online "hash lookup" sites won't help - the salt defeats them.
3. To count, submit the secret phrase **and** the code you used to find piece 3
   and verify the final hash.

## Stuck? Ask an organizer for these one at a time.

- **Hint A:** Piece 1 is in the 1890s.
- **Hint B:** Piece 2 is German and is 4 letters long.
- **Hint C:** For piece 3, download any big English wordlist, filter to 6-letter
   words, and hash each one - the match's hash starts `8a62e`.

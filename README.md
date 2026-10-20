# The Farm Hash Challenge

Somewhere behind this hash is a secret phrase. Your job is to find it, by any means possible: your brain, an AI assistant, code, or (ideally) all three.

## What you get

`challenge.json` contains everything you need:

```json
{
  "algorithm": "sha256",
  "format": "sha256(salt + secret), UTF-8, lowercase hex",
  "salt": "stanford-2026-yo:",
  "hash": "e6385f489beff26b65e2b2d2df50e5d8201ceccc38f7ec9fa664bf50513ac597"
}
```

In plain words: someone took the salt, stuck the secret phrase on the end, ran it through SHA-256, and gave you the result. You can't "decrypt" a hash. You can only guess phrases, hash them the same way, and see if you get a match.

## Hint key

The secret is 17 letters long, no spaces, numbers, or symbols. It's three English words glued together.

| Word | Length | Case | Clue |
|------|--------|------|------|
| 1 | 8 | all lowercase | The official name of "The Farm." |
| 2 | 2 | all lowercase | The most common linking verb in English. |
| 3 | 7 | First letter capitalized, rest lowercase | A compliment. Your code will have to find this one. |

## Rules

1. Any tool is allowed: AI chatbots, wordlists, Google, your friends.
2. Pasting the hash into an online "hash lookup" site won't work because of the salt. Don't bother.
3. To count, submit **both** the secret phrase **and** the code you used to confirm it. A lucky guess without a script that proves it doesn't count.

## Extra hints (only if you're stuck)

Ask an organizer for these one at a time.

- **Hint A:** Word 3 starts with a vowel.
- **Hint B:** You don't need a list of compliments. Any big list of English words will do; just filter it to 7 letters.
- **Hint C:** Word 3 ends with the letter "e".

Good luck!

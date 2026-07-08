Additional reviewer conventions:
- Prefer idiomatic constructs for the language at hand (e.g. list/dict comprehensions in Python,
  streams in Java, `next()`/`Optional` over manual find-loops) over verbose manual loops when it
  improves clarity without hurting readability.
- Flag missing input validation at trust boundaries (user input, network responses, file parsing)
  but do not demand validation for internal-only code paths.
- When reviewing a diff, focus comments on the changed lines; only mention surrounding code if
  it's directly relevant to a bug in the diff.

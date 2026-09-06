# Agent notes

- Prefer the minimum code that gets the job done, without making it harder to
  read. Don't write a field, config option, or line just because it's available
  or "more explicit" — if something works correctly without it (verify this,
  don't assume), leave it out.
- No code is the best code. Before adding something, check whether it's actually
  required (e.g. does the platform already default to the right behavior) rather
  than writing it preemptively.

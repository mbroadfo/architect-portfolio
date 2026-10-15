"""The local-first Studio (L2, ADR-013).

The Studio runs only on the owner's machine. Content lives in a private Git repository
separate from the public code repository; the public site is generated only from the frozen
published versions in that repository, and is scanned before it replaces the previous build.
"""

# local

The local development stack. Everything in this folder is **local-only**: it is never
built into a deployable artifact, and the fake-identity-provider guard
(`scripts/guard_fake_idp.py`) fails CI if any of it leaks into one.

- `fake-idp/` will hold the local stand-in for the identity provider. Its source carries the
  marker `AIDLC_LOCAL_ONLY_FAKE_IDP`, and its signing key exists only in memory.
- The walking slice (U0, S1 to S3) adds its Docker Compose stack and run instructions on its
  demonstration branch only; see `SLICE.md` there.

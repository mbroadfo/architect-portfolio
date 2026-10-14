"""AIDLC_LOCAL_ONLY_FAKE_IDP

LOCAL-ONLY FAKE identity provider for the walking slice (U0). It stands in for Auth0 on the
developer's machine only. It must never be deployed or packaged into a non-local artifact:
the S0 guard (scripts/guard_fake_idp.py) fails CI if this marker, the package name or the
fake issuer URL appears in any build output.
"""

MARKER = "AIDLC_LOCAL_ONLY_FAKE_IDP"

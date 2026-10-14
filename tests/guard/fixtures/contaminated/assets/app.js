// Synthetic negative fixture for the fake identity provider guard (AC0.2).
// It is NOT a real build output and holds no key: it only carries the marker text that the
// guard must detect in any non-local artifact.
export const leakedMarker = "AIDLC_LOCAL_ONLY_FAKE_IDP";
export function greet() {
  return "hello";
}

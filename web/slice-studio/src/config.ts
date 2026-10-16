// Local endpoints for the walking slice Studio page (S3). Defaults match local/compose.yaml.
// The token URL is the LOCAL-ONLY fake identity provider's, the local stand-in for sign-in.
const env = import.meta.env;

/**
 * The sign-in below defaults to the LOCAL-ONLY fake identity provider, so this page carries
 * the same marker as the fake provider. The marker is rendered into the page (App.tsx), which
 * keeps it in the built bundle: scripts/guard_fake_idp.py fails on any build of this Studio
 * (R-06). The slice Studio is never deployed.
 */
export const LOCAL_ONLY_FAKE_IDP_MARKER = "AIDLC_LOCAL_ONLY_FAKE_IDP";

export const API_BASE: string = env.VITE_API_BASE ?? "http://localhost:8000";
export const TOKEN_URL: string = env.VITE_TOKEN_URL ?? "http://localhost:9000/token";
export const OWNER_SUBJECT: string = env.VITE_OWNER_SUBJECT ?? "local-owner";

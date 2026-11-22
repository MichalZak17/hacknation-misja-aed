/**
 * The documentation (/docs) is internal for now: shown under `next dev`, gone from production builds (no nav links,
 * every /docs URL is a 404). Next inlines NODE_ENV, so this works in client and server code alike.
 */
export const DOCS_ENABLED = process.env.NODE_ENV !== "production";

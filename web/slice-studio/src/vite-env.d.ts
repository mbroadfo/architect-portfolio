/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_TOKEN_URL?: string;
  readonly VITE_OWNER_SUBJECT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

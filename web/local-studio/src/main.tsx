import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles/fonts/fonts.css";
import "./styles/prototype-styles.css";
import "./styles/prototype-studio.css";
import "./styles/local.css";

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

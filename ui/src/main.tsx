import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

// Simple CSS reset
const style = document.createElement("style");
style.textContent = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { line-height: 1.5; -webkit-font-smoothing: antialiased; }
  button { font-family: inherit; }
  textarea { font-family: inherit; }
  ::-webkit-scrollbar { width: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 9999px; }
`;
document.head.appendChild(style);

const root = document.getElementById("root");
if (!root) throw new Error("Root element not found");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>
);

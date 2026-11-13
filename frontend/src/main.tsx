/**
 * ==============================================================================
 * Privacy Gateway AI (MINEARENA PS-02) — Application Entry Point
 * ==============================================================================
 * Tech Stack:
 *  - React 19 / ReactDOM Client: Core UI rendering engine
 *  - Vite: Fast ESM-based development server and production bundler
 *  - Tailwind CSS: Utility-first design system via `./index.css`
 *
 * Purpose:
 *  - Mounts the root React component tree into the DOM (`#root`).
 *  - Enforces React.StrictMode for detecting side effects and lifecycle warnings.
 * ==============================================================================
 */

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

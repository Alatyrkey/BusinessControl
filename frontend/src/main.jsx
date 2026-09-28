import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MaxUI } from "@maxhub/max-ui";
import "@maxhub/max-ui/dist/styles.css";

import App from "./App.jsx";
import "./index.css";

const container = document.getElementById("root");

if (!container) {
  throw new Error("Не найден элемент #root в index.html");
}

createRoot(container).render(
  <StrictMode>
    <MaxUI>
      <App />
    </MaxUI>
  </StrictMode>,
);
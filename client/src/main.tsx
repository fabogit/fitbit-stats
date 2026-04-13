import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Provider } from "react-redux";
import "./index.css";
import App from "./App";
import { store } from "./store/store";
import { ThemeManager } from "./components/theme/ThemeManager";

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Provider store={store}>
      <ThemeManager />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />} />
          {/* Redirect old dashboard path to home */}
          <Route path="/dashboard" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </Provider>
  </StrictMode>
);

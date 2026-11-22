import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Provider } from "react-redux";
import "./index.css";
import App from "./App";
import { store } from "./store/store";
import { ThemeManager } from "./components/theme/ThemeManager";

document.title = `FitStats v${__APP_VERSION__}`;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Provider store={store}>
      <ThemeManager />
      <App />
    </Provider>
  </StrictMode>
);

import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  selectThemeMode,
  setResolvedTheme,
  selectResolvedTheme,
} from "../../store/slices/themeSlice";
import type { AppDispatch } from "../../store/store";

export const ThemeManager = () => {
  const dispatch = useDispatch<AppDispatch>();
  const mode = useSelector(selectThemeMode);
  const resolvedTheme = useSelector(selectResolvedTheme);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    const calculateTheme = () => {
      if (mode === "system") {
        const systemTheme = mediaQuery.matches ? "dark" : "light";
        dispatch(setResolvedTheme(systemTheme));
      } else {
        dispatch(setResolvedTheme(mode));
      }
    };

    calculateTheme();

    const handleSystemChange = () => {
      if (mode === "system") calculateTheme();
    };

    mediaQuery.addEventListener("change", handleSystemChange);

    return () => {
      mediaQuery.removeEventListener("change", handleSystemChange);
    };
  }, [mode, dispatch]);

  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(resolvedTheme);
    root.setAttribute("data-theme", resolvedTheme);
    root.style.colorScheme = resolvedTheme;
  }, [resolvedTheme]);

  return null;
};

import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

export type ThemeMode = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

interface ThemeState {
  mode: ThemeMode;
  resolvedTheme: ResolvedTheme;
}

const getInitialMode = (): ThemeMode => {
  if (typeof window !== "undefined") {
    const savedMode = localStorage.getItem("theme-mode") as ThemeMode;
    if (savedMode && ["light", "dark", "system"].includes(savedMode)) {
      return savedMode;
    }
  }
  return "system";
};

const initialState: ThemeState = {
  mode: getInitialMode(),
  resolvedTheme: "light",
};

const themeSlice = createSlice({
  name: "theme",
  initialState,
  reducers: {
    setThemeMode: (state, action: PayloadAction<ThemeMode>) => {
      state.mode = action.payload;
      localStorage.setItem("theme-mode", action.payload);
    },
    setResolvedTheme: (state, action: PayloadAction<ResolvedTheme>) => {
      state.resolvedTheme = action.payload;
    },
  },
});

export const { setThemeMode, setResolvedTheme } = themeSlice.actions;

export const selectThemeMode = (state: { theme: ThemeState }) =>
  state.theme.mode;
export const selectResolvedTheme = (state: { theme: ThemeState }) =>
  state.theme.resolvedTheme;

export default themeSlice.reducer;

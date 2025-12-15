import { configureStore } from "@reduxjs/toolkit";
import {
  useDispatch,
  useSelector,
  type TypedUseSelectorHook,
} from "react-redux";
import dashboardReducer from "@/features/dashboard/dashboardSlice";
import themeReducer from "./slices/themeSlice";

export const store = configureStore({
  reducer: {
    dashboard: dashboardReducer,
    theme: themeReducer,
  },
});

// Infer types
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Custom hooks typed
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

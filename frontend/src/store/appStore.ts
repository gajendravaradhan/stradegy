import { create } from "zustand";

interface AppState {
  autonomyMode: "semi" | "full";
  tradeMode: "paper" | "live";
  setAutonomyMode: (mode: "semi" | "full") => void;
  setTradeMode: (mode: "paper" | "live") => void;
}

export const useAppStore = create<AppState>((set) => ({
  autonomyMode: "semi",
  tradeMode: "paper",
  setAutonomyMode: (mode) => set({ autonomyMode: mode }),
  setTradeMode: (mode) => set({ tradeMode: mode }),
}));

import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import { QueryClient } from "@tanstack/react-query";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister";
import { registerSW } from "virtual:pwa-register";
import App from "./App";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
      refetchOnWindowFocus: false,
      gcTime: 1000 * 60 * 60 * 24,
    },
  },
});

const persister = createSyncStoragePersister({
  storage: window.localStorage,
  key: "stradegy-query-cache",
});

const updateSW = registerSW({
  onNeedRefresh() {
    if (confirm("A new version is available. Reload?")) {
      updateSW(true);
    }
  },
  onOfflineReady() {
    console.log("Stradegy ready for offline use");
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <PersistQueryClientProvider client={queryClient} persistOptions={{ persister }}>
      <HashRouter>
        <App />
      </HashRouter>
    </PersistQueryClientProvider>
  </React.StrictMode>,
);

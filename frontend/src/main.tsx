import React from "react";
import ReactDOM from "react-dom/client";
import AIPlaylistPage from "./pages/AIPlaylistPage";
import "./index.css";

// AI DJ Studio is now the main (and only) page
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AIPlaylistPage />
  </React.StrictMode>
);

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import AIPlaylistPage from "./pages/AIPlaylistPage";
import "./index.css";

// Simple hash-based routing
function Router() {
  const [route, setRoute] = React.useState(window.location.hash || "#/");

  React.useEffect(() => {
    const handleHashChange = () => setRoute(window.location.hash || "#/");
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  if (route === "#/ai-dj") {
    return <AIPlaylistPage />;
  }

  return <App />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Router />
  </React.StrictMode>
);

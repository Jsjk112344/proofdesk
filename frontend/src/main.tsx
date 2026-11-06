import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { DealerApp } from "./dealer";
import { LegacyApp } from "./legacy";
import "./style.css";
import "./dealer.css";

function App() {
  const [hash, setHash] = useState(location.hash);
  useEffect(() => { const update = () => setHash(location.hash); window.addEventListener("hashchange", update); return () => window.removeEventListener("hashchange", update); }, []);
  return /^#\/(legacy|experiments|prospects|queue)(\/|$)/.test(hash) ? <LegacyApp /> : <DealerApp />;
}
createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);

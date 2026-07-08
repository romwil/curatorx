import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import App from "./App";
import TitleDetailPage from "./pages/TitleDetailPage";
import ConfigPage from "./pages/ConfigPage";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/config" element={<ConfigPage />} />
        <Route path="/title/:mediaType/:itemId" element={<TitleDetailPage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);

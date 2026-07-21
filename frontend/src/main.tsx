// Ponto de entrada do frontend: monta o componente <App /> dentro da div
// #root (declarada em index.html) usando a API do React 18 (createRoot).
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css"; // carrega as diretivas do Tailwind (@tailwind base/components/utilities)

// "!" depois de getElementById diz ao TypeScript "confio que esse elemento existe"
// (ele existe sempre, pois index.html sempre tem <div id="root">).
ReactDOM.createRoot(document.getElementById("root")!).render(
  // StrictMode ativa checagens extras do React só em desenvolvimento
  // (ajuda a pegar efeitos colaterais indevidos cedo); não afeta produção.
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

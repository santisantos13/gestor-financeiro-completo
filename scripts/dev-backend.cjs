#!/usr/bin/env node
/**
 * Inicia o backend (uvicorn) a partir da raiz do projeto, resolvendo o
 * Python do virtualenv de forma portátil (Windows/Mac/Linux) - não existe
 * um comando único "source .venv/bin/activate" que funcione nos três, então
 * este script chama o binário do venv diretamente pelo caminho certo do SO.
 *
 * Pré-requisito (uma vez só, ver README > "Ambiente de Desenvolvimento"):
 *   cd backend && python -m venv .venv && <ativar> && pip install -r requirements.txt
 *   cp .env.example .env  (e definir SECRET_KEY)
 *   alembic upgrade head
 *
 * Sem isso, este script para com uma mensagem explicando o que falta -
 * nunca falha silenciosamente nem tenta "consertar" o ambiente sozinho.
 */
const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");

const backendDir = path.join(__dirname, "..", "backend");
const isWindows = process.platform === "win32";
const venvPython = path.join(
  backendDir,
  ".venv",
  isWindows ? "Scripts" : "bin",
  isWindows ? "python.exe" : "python",
);
const envFile = path.join(backendDir, ".env");

function fail(message) {
  console.error(`\n[backend] ${message}\n`);
  process.exit(1);
}

if (!fs.existsSync(venvPython)) {
  fail(
    "Virtualenv não encontrado em backend/.venv. Configuração inicial (uma vez):\n\n" +
      "  cd backend\n" +
      "  python -m venv .venv\n" +
      (isWindows ? "  .venv\\Scripts\\activate\n" : "  source .venv/bin/activate\n") +
      "  pip install -r requirements.txt\n" +
      "  " + (isWindows ? "copy .env.example .env" : "cp .env.example .env") + "   (edite e defina um SECRET_KEY proprio)\n" +
      "  alembic upgrade head\n\n" +
      "Depois disso, `npm run dev:full` (ou `npm run dev:backend`) funciona.",
  );
}

if (!fs.existsSync(envFile)) {
  fail(
    "backend/.env não encontrado. Copie backend/.env.example para backend/.env " +
      "e defina um SECRET_KEY (veja o comentário no arquivo) antes de continuar.",
  );
}

console.log("[backend] iniciando uvicorn em http://localhost:8000 ...");

const child = spawn(venvPython, ["-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"], {
  cwd: backendDir,
  stdio: "inherit",
});

child.on("exit", (code) => process.exit(code ?? 0));

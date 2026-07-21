// ============================================================
// Finanças Pessoais — Painel do Projeto
// Renderiza tudo a partir de project-status.json. Não há dados
// "hardcoded" aqui: para atualizar o painel, edite o JSON.
// Faz polling a cada 30s para refletir mudanças no arquivo sem
// precisar recarregar a página manualmente.
// ============================================================

const DATA_URL = "./project-status.json";
const POLL_MS = 30000;

const STATUS_LABEL = {
  done: "Concluído",
  "in-progress": "Em andamento",
  pending: "Pendente",
  blocked: "Bloqueada",
};

const CHANGELOG_DOT = {
  backend: "#3ecf8e",
  frontend: "#6d5ef5",
  design: "#f5b942",
  docs: "#8b8b96",
  tooling: "#8577ff",
  security: "#f5606d",
  "full-stack": "#5f9df7",
};

// Colunas ativas do quadro kanban - "done" NÃO entra aqui: com dezenas de
// entregas concluídas (cada uma com uma descrição de parágrafo inteiro),
// misturar tudo no mesmo grid virava uma parede de texto impossível de
// escanear. "done" ganhou sua própria seção searchável/colapsável logo
// abaixo (ver renderKanbanDone).
const KANBAN_COLUMNS = [
  { key: "backlog", label: "Backlog" },
  { key: "in-development", label: "Em desenvolvimento" },
  { key: "review", label: "Revisão" },
];

let currentData = null;
let currentFilter = "all";
let lastRawJson = null;
let doneSearchTerm = "";
let changelogSearchTerm = "";

async function fetchData() {
  const res = await fetch(`${DATA_URL}?_=${Date.now()}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Falha ao carregar ${DATA_URL}: ${res.status}`);
  const raw = await res.text();
  return { raw, data: JSON.parse(raw) };
}

function fmtDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function relativeTime(iso) {
  if (!iso) return "";
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return "agora mesmo";
  if (mins < 60) return `há ${mins} min`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `há ${hours} h`;
  const days = Math.round(hours / 24);
  return `há ${days} d`;
}

function fmtDateShort(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

function el(tag, className, html) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (html !== undefined) e.innerHTML = html;
  return e;
}

/** Normaliza texto pra busca: minúsculo + sem acento, pra "faturas" achar
 * "Faturas"/"fatúras" indiferente de como o usuário digitou. */
function normalizar(texto) {
  return (texto || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}

// ---------- Header ----------

function renderHeader(data) {
  document.getElementById("project-name").textContent = data.project.name;
  document.getElementById("project-tagline").textContent = data.project.tagline;
  document.getElementById("project-status-label").textContent = `${data.project.status.emoji} ${data.project.status.label}`;
  const updatedEl = document.getElementById("updated-at");
  updatedEl.textContent = `Atualizado ${relativeTime(data.project.updatedAt)}`;
  updatedEl.title = fmtDateTime(data.project.updatedAt);
}

// ---------- Overview ----------

function renderOverview(data) {
  document.getElementById("overview-percent").textContent = `${data.project.overallPercent}%`;
  const circumference = 2 * Math.PI * 60;
  const ring = document.getElementById("overview-ring-fill");
  const offset = circumference * (1 - data.project.overallPercent / 100);
  requestAnimationFrame(() => {
    ring.style.strokeDashoffset = offset;
  });

  // Estatísticas rápidas: dá pra responder "quanto já foi feito" sem
  // precisar rolar até o Kanban ou o Changelog.
  const totalDone = (data.kanban?.done || []).length;
  const totalChangelog = (data.changelog || []).length;
  const statsWrap = document.getElementById("overview-stats");
  statsWrap.innerHTML = "";
  const stats = [
    { value: totalDone, label: "entregas concluídas" },
    { value: totalChangelog, label: "itens no histórico" },
    { value: `${data.quality.featuresRatio.done}/${data.quality.featuresRatio.total}`, label: data.quality.featuresRatio.label },
  ];
  stats.forEach((s) => {
    const stat = el("div", "overview-stat");
    stat.appendChild(el("span", "overview-stat__value", String(s.value)));
    stat.appendChild(el("span", "overview-stat__label", s.label));
    statsWrap.appendChild(stat);
  });

  const q = data.quality;
  const strip = document.getElementById("quality-strip");
  strip.innerHTML = "";
  const chips = [
    { label: "Testes backend", value: q.testCoverage.backend },
    { label: "Testes frontend", value: q.testCoverage.frontend },
    { label: "Débitos técnicos", value: `${q.technicalDebt} conhecidos` },
    { label: "Documentação", value: `${q.documentation}%` },
    { label: "Segurança", value: `${q.security}%` },
  ];
  chips.forEach((c) => {
    const chip = el("div", "quality-chip");
    chip.title = c.value; // texto completo no hover - valores longos (ex:
    // contagem de testes com contexto) não cabem no chip, mas continuam
    // acessíveis sem precisar ir a lugar nenhum.
    chip.appendChild(el("span", "quality-chip__label", c.label));
    chip.appendChild(el("span", "quality-chip__value", c.value));
    strip.appendChild(chip);
  });
}

// ---------- Areas ----------

function renderAreas(data) {
  const grid = document.getElementById("areas-grid");
  grid.innerHTML = "";
  data.areas.forEach((area, i) => {
    const card = el("div", "area-card");
    card.style.animationDelay = `${i * 40}ms`;
    card.innerHTML = `
      <div class="area-card__top">
        <span class="area-card__label">${area.label}</span>
        <span class="area-card__percent">${area.percent}%</span>
      </div>
      <div class="area-card__bar"><div class="area-card__bar-fill" data-target="${area.percent}"></div></div>
      <div class="area-card__stats">
        <span><span class="dot dot--done"></span>${area.done} concluídas</span>
        <span><span class="dot dot--progress"></span>${area.inProgress} em curso</span>
        <span><span class="dot dot--pending"></span>${area.pending} pendentes</span>
      </div>
    `;
    grid.appendChild(card);
  });
  requestAnimationFrame(() => {
    grid.querySelectorAll(".area-card__bar-fill").forEach((bar) => {
      bar.style.width = `${bar.dataset.target}%`;
    });
  });
}

// ---------- Roadmap ----------
// Fases "done" nascem recolhidas (só o título + badge) - já são passado,
// não precisam competir por atenção com o que está em andamento/pendente.
// Um clique no cabeçalho (ou os botões expandir/recolher tudo) alterna.

function renderRoadmap(data) {
  const wrap = document.getElementById("roadmap");
  wrap.innerHTML = "";
  data.roadmap.forEach((phase, i) => {
    const colapsada = phase.status === "done";
    const row = el("div", `roadmap-phase roadmap-phase--${phase.status}${colapsada ? " roadmap-phase--collapsed" : ""}`);
    row.style.animationDelay = `${i * 60}ms`;
    const isLast = i === data.roadmap.length - 1;
    row.innerHTML = `
      <div class="roadmap-phase__rail">
        <div class="roadmap-phase__dot"></div>
        ${isLast ? "" : '<div class="roadmap-phase__line"></div>'}
      </div>
      <div class="roadmap-phase__body">
        <div class="roadmap-phase__head" data-role="roadmap-toggle">
          <span class="roadmap-phase__name">${phase.phase}</span>
          <span class="roadmap-phase__title">${phase.title}</span>
          <span class="badge badge--${phase.status}">${STATUS_LABEL[phase.status]}</span>
          <span class="roadmap-phase__chevron">▾</span>
        </div>
        <ul class="roadmap-phase__items">
          ${phase.items.map((it) => `<li>${it}</li>`).join("")}
        </ul>
      </div>
    `;
    wrap.appendChild(row);
  });
}

function setupRoadmapControls() {
  document.getElementById("roadmap").addEventListener("click", (event) => {
    const head = event.target.closest('[data-role="roadmap-toggle"]');
    if (!head) return;
    head.closest(".roadmap-phase").classList.toggle("roadmap-phase--collapsed");
  });
  document.getElementById("roadmap-expand-all").addEventListener("click", () => {
    document.querySelectorAll(".roadmap-phase").forEach((p) => p.classList.remove("roadmap-phase--collapsed"));
  });
  document.getElementById("roadmap-collapse-all").addEventListener("click", () => {
    document.querySelectorAll(".roadmap-phase").forEach((p) => p.classList.add("roadmap-phase--collapsed"));
  });
}

// ---------- Features table ----------

function renderFeatures(data) {
  const tbody = document.getElementById("features-tbody");
  tbody.innerHTML = "";
  const rows = data.features.filter((f) => currentFilter === "all" || f.status === currentFilter);
  if (rows.length === 0) {
    const tr = el("tr");
    tr.innerHTML = `<td colspan="5" style="text-align:center; color:var(--text-tertiary); padding:24px;">Nenhuma funcionalidade nesse filtro.</td>`;
    tbody.appendChild(tr);
    return;
  }
  rows.forEach((f) => {
    const tr = el("tr");
    tr.innerHTML = `
      <td>${f.name}</td>
      <td>${f.category}</td>
      <td><span class="badge badge--${f.status}">${STATUS_LABEL[f.status]}</span></td>
      <td>
        <div class="progress-cell">
          <div class="progress-track"><div class="progress-fill" data-target="${f.progress}"></div></div>
          <span class="progress-label">${f.progress}%</span>
        </div>
      </td>
      <td><span class="priority priority--${f.priority.toLowerCase()}">${f.priority}</span></td>
    `;
    tbody.appendChild(tr);
  });
  requestAnimationFrame(() => {
    tbody.querySelectorAll(".progress-fill").forEach((bar) => {
      bar.style.width = `${bar.dataset.target}%`;
    });
  });
}

function setupFilters() {
  const container = document.getElementById("feature-filters");
  container.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      currentFilter = btn.dataset.filter;
      container.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      renderFeatures(currentData);
    });
  });
}

// ---------- Kanban (board ativo) ----------

function renderKanban(data) {
  const wrap = document.getElementById("kanban");
  wrap.innerHTML = "";
  KANBAN_COLUMNS.forEach((col) => {
    const items = data.kanban[col.key] || [];
    const colEl = el("div", "kanban-col");
    const head = el("div", "kanban-col__head");
    head.innerHTML = `<span class="kanban-col__title">${col.label}</span><span class="kanban-col__count">${items.length}</span>`;
    colEl.appendChild(head);
    if (items.length === 0) {
      colEl.appendChild(el("div", "kanban-empty", "Nenhuma tarefa"));
    } else {
      items.forEach((task, i) => {
        const card = el("div", "kanban-card");
        card.style.animationDelay = `${i * 40}ms`;
        card.innerHTML = `
          <span class="kanban-card__title">${task.title}</span>
          <span class="kanban-card__desc">${task.description}</span>
          <div class="kanban-card__foot">
            <span class="kanban-card__tag">${task.category} · ${task.priority}</span>
            <span class="kanban-card__date">${fmtDateShort(task.date)}</span>
          </div>
        `;
        colEl.appendChild(card);
      });
    }
    wrap.appendChild(colEl);
  });
}

// ---------- Kanban: log de entregas concluídas ----------
// Por que uma seção separada, searchável, colapsada por padrão: uma
// entrega concluída aqui costuma ter uma descrição de parágrafo inteiro
// (documentando achados/decisões da etapa) - com dezenas delas, um card de
// Kanban tradicional virava uma parede de texto impossível de escanear.
// Aqui cada entrega é uma linha (título + categoria + data); o parágrafo
// só aparece ao clicar, e uma busca por texto acha qualquer uma sem rolar.

function renderKanbanDone(data) {
  const items = data.kanban.done || [];
  document.getElementById("done-count").textContent = String(items.length);
  const list = document.getElementById("done-list");
  list.innerHTML = "";
  items
    .slice()
    .reverse() // mais recente primeiro
    .forEach((task, i) => {
      const busca = normalizar(`${task.title} ${task.description} ${task.category}`);
      const item = el("div", "done-item");
      item.dataset.search = busca;
      item.style.animationDelay = `${Math.min(i, 12) * 25}ms`;
      item.innerHTML = `
        <button type="button" class="done-item__head" data-role="done-toggle">
          <span class="done-item__chevron">▸</span>
          <span class="done-item__title">${task.title}</span>
          <span class="done-item__meta">${task.category} · ${fmtDateShort(task.date)}</span>
        </button>
        <div class="done-item__body">
          <p class="done-item__desc">${task.description}</p>
        </div>
      `;
      list.appendChild(item);
    });
  aplicarBuscaDone();
}

function aplicarBuscaDone() {
  const termo = normalizar(doneSearchTerm.trim());
  const itens = document.querySelectorAll("#done-list .done-item");
  let visiveis = 0;
  itens.forEach((item) => {
    const bate = termo === "" || item.dataset.search.includes(termo);
    item.classList.toggle("is-hidden", !bate);
    if (bate) visiveis += 1;
  });
  document.getElementById("done-empty").hidden = visiveis > 0 || itens.length === 0;
}

function setupDoneControls() {
  document.getElementById("done-search").addEventListener("input", (event) => {
    doneSearchTerm = event.target.value;
    aplicarBuscaDone();
  });
  document.getElementById("done-list").addEventListener("click", (event) => {
    const head = event.target.closest('[data-role="done-toggle"]');
    if (!head) return;
    head.closest(".done-item").classList.toggle("is-open");
  });
  document.getElementById("done-expand-all").addEventListener("click", () => {
    document.querySelectorAll("#done-list .done-item").forEach((i) => i.classList.add("is-open"));
  });
  document.getElementById("done-collapse-all").addEventListener("click", () => {
    document.querySelectorAll("#done-list .done-item").forEach((i) => i.classList.remove("is-open"));
  });
}

// ---------- Changelog ----------
// Mesma lógica de truncamento do log de entregas: título longo (alguns
// passam de 200 caracteres) corta em 3 linhas com "ver mais", e um campo
// de busca acha qualquer item sem precisar rolar um histórico que só
// cresce.

function renderChangelog(data) {
  const wrap = document.getElementById("changelog");
  wrap.innerHTML = "";
  const termo = normalizar(changelogSearchTerm.trim());
  let visiveis = 0;
  data.changelog.forEach((item, i) => {
    const busca = normalizar(`${item.title} ${item.type}`);
    if (termo !== "" && !busca.includes(termo)) return;
    visiveis += 1;
    const row = el("div", "changelog-item");
    row.style.animationDelay = `${Math.min(i, 12) * 40}ms`;
    const dotColor = CHANGELOG_DOT[item.type] || "#8b8b96";
    row.innerHTML = `
      <span class="changelog-item__date">${item.date ? fmtDateShort(item.date) : item.dateLabel}</span>
      <span class="changelog-item__rail"><span class="changelog-item__dot" style="background:${dotColor}"></span></span>
      <span>
        <span class="changelog-item__type">${item.type}</span>
        <div class="changelog-item__title clamp-3" data-role="changelog-text">${item.title}</div>
        <button type="button" class="clamp-toggle" data-role="changelog-toggle" hidden>Ver mais</button>
      </span>
    `;
    wrap.appendChild(row);
  });
  document.getElementById("changelog-empty").hidden = visiveis > 0;

  // só mostra "Ver mais" em quem de fato transbordou as 3 linhas -
  // comparar scrollHeight com clientHeight depois do layout resolver.
  requestAnimationFrame(() => {
    wrap.querySelectorAll('[data-role="changelog-text"]').forEach((textEl) => {
      const btn = textEl.parentElement.querySelector('[data-role="changelog-toggle"]');
      if (textEl.scrollHeight > textEl.clientHeight + 2) {
        btn.hidden = false;
      }
    });
  });
}

function setupChangelogControls() {
  document.getElementById("changelog-search").addEventListener("input", (event) => {
    changelogSearchTerm = event.target.value;
    renderChangelog(currentData);
  });
  document.getElementById("changelog").addEventListener("click", (event) => {
    const btn = event.target.closest('[data-role="changelog-toggle"]');
    if (!btn) return;
    const textEl = btn.previousElementSibling;
    const aberto = textEl.classList.toggle("changelog-item__title--expanded");
    textEl.classList.toggle("clamp-3", !aberto);
    btn.textContent = aberto ? "Ver menos" : "Ver mais";
  });
}

// ---------- Architecture ----------

function renderArchitecture(data) {
  const wrap = document.getElementById("architecture");
  const arch = data.architecture;
  wrap.innerHTML = "";
  const flow = el("div", "arch-flow");
  arch.layers.forEach((layer, i) => {
    flow.appendChild(el("div", "arch-flow__node", layer));
    if (i < arch.layers.length - 1) flow.appendChild(el("span", "arch-flow__arrow", "→"));
  });
  wrap.appendChild(flow);

  const stacks = el("div", "arch-stacks");
  const labels = { frontend: "Frontend", backend: "Backend", database: "Banco de dados" };
  Object.keys(arch.technologies).forEach((key) => {
    const stack = el("div", "arch-stack");
    stack.appendChild(el("div", "arch-stack__title", labels[key] || key));
    const tags = el("div", "arch-stack__tags");
    arch.technologies[key].forEach((t) => tags.appendChild(el("span", "tech-tag", t)));
    stack.appendChild(tags);
    stacks.appendChild(stack);
  });
  wrap.appendChild(stacks);
}

// ---------- Orchestration ----------

function renderAll(data) {
  currentData = data;
  renderHeader(data);
  renderOverview(data);
  renderAreas(data);
  renderRoadmap(data);
  renderFeatures(data);
  renderKanban(data);
  renderKanbanDone(data);
  renderChangelog(data);
  renderArchitecture(data);
}

async function load(isPoll) {
  try {
    const { raw, data } = await fetchData();
    if (isPoll && raw === lastRawJson) return; // sem mudanças, não re-renderiza
    lastRawJson = raw;
    renderAll(data);
    if (!isPoll) {
      setupFilters();
      setupRoadmapControls();
      setupDoneControls();
      setupChangelogControls();
    }
  } catch (err) {
    console.error(err);
    if (!isPoll) {
      document.querySelector(".shell").innerHTML =
        `<div class="panel" style="padding:24px;">Não foi possível carregar <code>project-status.json</code>. Verifique se o painel está sendo servido por um servidor local (veja o README) e se o arquivo existe na mesma pasta.</div>`;
    }
  }
}

load(false);
setInterval(() => load(true), POLL_MS);
setInterval(() => {
  if (currentData) {
    const updatedEl = document.getElementById("updated-at");
    updatedEl.textContent = `Atualizado ${relativeTime(currentData.project.updatedAt)}`;
  }
}, 60000);

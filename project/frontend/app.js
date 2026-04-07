/* ═══════════════════════════════════════════
   ArmorClaw — Frontend Logic
   ═══════════════════════════════════════════ */
const API = "http://localhost:8000";

// ── Rotating Hero Word ──
const heroWords = ["autonomous", "intelligent", "secure", "real-time", "compliant"];
let wordIdx = 0;
const rotEl = document.getElementById("rotating-word");
if (rotEl) {
  setInterval(() => {
    rotEl.style.opacity = "0";
    rotEl.style.transform = "translateY(-12px)";
    setTimeout(() => {
      wordIdx = (wordIdx + 1) % heroWords.length;
      rotEl.textContent = heroWords[wordIdx];
      rotEl.style.transform = "translateY(12px)";
      requestAnimationFrame(() => {
        rotEl.style.opacity = "1";
        rotEl.style.transform = "translateY(0)";
      });
    }, 300);
  }, 2200);
  rotEl.style.transition = "opacity .3s, transform .3s";
}

// ── 3D Scroll Card ──
const card3d = document.getElementById("card3d");
const scroll3d = document.getElementById("scroll3d");
if (card3d && scroll3d) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      const ratio = e.intersectionRatio;
      const rx = 12 * (1 - ratio);
      const s = 0.97 + 0.03 * ratio;
      card3d.style.transform = `rotateX(${rx}deg) scale(${s})`;
    });
  }, { threshold: Array.from({ length: 20 }, (_, i) => i / 19) });
  observer.observe(scroll3d);
}

// ── Reveal on Scroll ──
const revealEls = document.querySelectorAll("[data-reveal]");
const revealObs = new IntersectionObserver((entries) => {
  entries.forEach((e) => { if (e.isIntersecting) e.target.classList.add("revealed"); });
}, { threshold: 0.15 });
revealEls.forEach((el) => revealObs.observe(el));

// ── Load Policies ──
async function loadPolicies() {
  try {
    const res = await fetch(API + "/api/policies");
    const data = await res.json();
    const grid = document.getElementById("policies-grid");
    if (!grid) return;
    grid.innerHTML = data.map((p) => `
      <div class="policy-card">
        <div class="policy-id">${p.id}</div>
        <div class="policy-rule">${p.rule}</div>
      </div>
    `).join("");
  } catch (e) { console.warn("Could not load policies", e); }
}

// ── Refresh Stats ──
async function refreshStats() {
  try {
    const res = await fetch(API + "/api/stats");
    const s = await res.json();
    document.getElementById("stat-total").textContent = s.total_actions;
    document.getElementById("stat-allowed").textContent = s.allowed;
    document.getElementById("stat-blocked").textContent = s.blocked;
    document.getElementById("stat-rate").textContent = s.block_rate + "%";
  } catch (e) { /* ignore */ }
}

// ── Refresh Logs ──
async function refreshLogs() {
  try {
    const res = await fetch(API + "/api/logs");
    const logs = await res.json();
    const tbody = document.getElementById("log-tbody");
    if (!tbody) return;
    if (logs.length === 0) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="8">No actions yet. Use the chat below to send commands.</td></tr>';
      return;
    }
    tbody.innerHTML = logs.map((l) => `
      <tr class="${l.allowed ? "log-allowed" : "log-blocked"}">
        <td>${l.timestamp}</td>
        <td>${l.command}</td>
        <td>${l.action}</td>
        <td>${l.symbol || "—"}</td>
        <td>${l.amount ? "$" + l.amount : "—"}</td>
        <td>${l.allowed ? '<span class="badge-success">Verified</span>' : '<span class="badge-error">Denied</span>'}</td>
        <td>${l.allowed ? "ALLOWED" : "BLOCKED"}</td>
        <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">${l.reason}</td>
      </tr>
    `).join("");
  } catch (e) { /* ignore */ }
}

// ── Chat ──
const chatInput = document.getElementById("chat-input");
const chatMessages = document.getElementById("chat-messages");
const chatSend = document.getElementById("chat-send");

if (chatInput) {
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendCommand(); }
  });
  chatInput.addEventListener("input", () => {
    chatInput.style.height = "24px";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
  });
}

function addMsg(text, type) {
  const div = document.createElement("div");
  div.className = "chat-msg " + type;
  div.innerHTML = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendCommand() {
  const cmd = chatInput.value.trim();
  if (!cmd) return;
  chatInput.value = "";
  chatInput.style.height = "24px";
  chatSend.disabled = true;

  addMsg(cmd, "user");

  // Typing indicator
  const typing = document.createElement("div");
  typing.className = "chat-msg bot";
  typing.innerHTML = '<span style="display:flex;gap:4px;align-items:center"><span class="dot-anim"></span><span class="dot-anim"></span><span class="dot-anim"></span></span>';
  typing.id = "typing-indicator";
  chatMessages.appendChild(typing);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  try {
    const res = await fetch(API + "/api/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: cmd }),
    });
    const data = await res.json();

    // Remove typing
    const ti = document.getElementById("typing-indicator");
    if (ti) ti.remove();

    const status = data.allowed ? "✅ ALLOWED" : "❌ BLOCKED";
    const cls = data.allowed ? "allowed" : "blocked";
    let msg = `<strong>${status}</strong><br>`;
    msg += `Action: <strong>${data.action}</strong>`;
    if (data.symbol) msg += ` | Symbol: <strong>${data.symbol}</strong>`;
    if (data.amount) msg += ` | Amount: <strong>$${data.amount}</strong>`;
    msg += `<br>Reason: ${data.reason}`;
    if (data.execution_result) msg += `<br><em>${data.execution_result}</em>`;

    addMsg(msg, "bot " + cls);
    refreshStats();
    refreshLogs();
  } catch (e) {
    const ti = document.getElementById("typing-indicator");
    if (ti) ti.remove();
    addMsg("⚠️ Could not connect to server. Is the backend running?", "bot blocked");
  }
  chatSend.disabled = false;
}

function quickCmd(cmd) {
  chatInput.value = cmd;
  sendCommand();
}

async function resetAll() {
  try {
    await fetch(API + "/api/reset", { method: "POST" });
    chatMessages.innerHTML = "";
    refreshStats();
    refreshLogs();
    addMsg("🔄 Demo reset. All counters cleared.", "bot");
  } catch (e) { alert("Could not reset."); }
}

// ── Typing dots animation via CSS ──
const dotStyle = document.createElement("style");
dotStyle.textContent = `
.dot-anim { width:6px; height:6px; background:rgba(255,255,255,.6); border-radius:50%; animation: dotBounce 1.2s infinite; }
.dot-anim:nth-child(2) { animation-delay:.15s; }
.dot-anim:nth-child(3) { animation-delay:.3s; }
@keyframes dotBounce { 0%,80%,100%{opacity:.3;transform:scale(.8)} 40%{opacity:1;transform:scale(1.2)} }
`;
document.head.appendChild(dotStyle);

// ── Init ──
loadPolicies();
refreshStats();
refreshLogs();
// Poll stats every 5s
setInterval(() => { refreshStats(); refreshLogs(); }, 5000);

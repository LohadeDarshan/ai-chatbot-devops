// ---- Config ----
// Frontend is served by nginx, which proxies /api, /health, /docs to the backend.
// So we can just use relative paths here — works in docker-compose AND k8s ingress.
const API_BASE = "";

// ---- Session ----
const sessionId = "session-" + Math.random().toString(36).slice(2, 10);
document.getElementById("session-id").textContent = "#" + sessionId;

// ---- Elements ----
const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const modelMeta = document.getElementById("model-meta");
const statusBackend = document.getElementById("status-backend");
const statusDb = document.getElementById("status-db");
const statusModel = document.getElementById("status-model");

function appendMessage(role, text) {
  const msg = document.createElement("div");
  msg.className = `msg ${role}`;
  const tag = document.createElement("span");
  tag.className = "msg-tag";
  tag.textContent = role === "user" ? "you" : "bot";
  const p = document.createElement("p");
  p.textContent = text;
  msg.appendChild(tag);
  msg.appendChild(p);
  chatWindow.appendChild(msg);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return msg;
}

function setPill(el, ok, text) {
  el.textContent = text;
  el.classList.remove("ok", "down");
  el.classList.add(ok ? "ok" : "down");
}

async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error("bad status");
    const data = await res.json();

    setPill(statusBackend, true, "fastapi :8000");
    setPill(statusDb, data.database === "ok", data.database === "ok" ? "postgres ok" : "postgres down");
    setPill(statusModel, true, data.model_backend);
    modelMeta.textContent = `model: ${data.model_backend}`;
  } catch (err) {
    setPill(statusBackend, false, "unreachable");
    setPill(statusDb, false, "unknown");
    setPill(statusModel, false, "unknown");
    modelMeta.textContent = "model: backend unreachable";
  }
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;

  appendMessage("user", text);
  messageInput.value = "";
  sendBtn.disabled = true;

  const typingMsg = appendMessage("bot", "thinking...");
  typingMsg.classList.add("typing");

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    typingMsg.querySelector("p").textContent = data.bot_response;
    typingMsg.classList.remove("typing");
  } catch (err) {
    typingMsg.querySelector("p").textContent = `Error: ${err.message}`;
    typingMsg.classList.remove("typing");
  } finally {
    sendBtn.disabled = false;
    messageInput.focus();
  }
});

// Initial + periodic health check
checkHealth();
setInterval(checkHealth, 15000);

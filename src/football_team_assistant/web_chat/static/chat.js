"use strict";

const CONVERSATIONS = "/chat/conversations";
const CREATE_TIMEOUT = 10_000;
const TURN_TIMEOUT = 95_000;
const composer = document.querySelector("#composer");
const message = document.querySelector("#message");
const send = document.querySelector("#send");
const transcript = document.querySelector("#transcript");
const messages = document.querySelector("#messages");
const statusLine = document.querySelector("#status");
const errorLine = document.querySelector("#error");
const retry = document.querySelector("#retry");
const welcome = document.querySelector("#welcome");
const newChat = document.querySelector("#new-chat");
const connection = document.querySelector("#connection");

function newPage() {
  return { id: null, busy: false, failed: null, needsFreshContext: false };
}

let page = newPage();

function updateControls() {
  send.disabled = page.busy || !page.id;
  newChat.disabled = page.busy || !page.id;
  retry.hidden = page.busy || (page.id !== null && page.failed === null);
  retry.textContent = page.needsFreshContext ? "Start fresh" : page.id ? "Retry" : "Reconnect";
  if (page.id) {
    connection.dataset.state = "ready";
    connection.textContent = "Local session";
  } else if (page.busy) {
    connection.dataset.state = "connecting";
    connection.textContent = "Connecting";
  } else {
    connection.dataset.state = "unavailable";
    connection.textContent = "Session unavailable";
  }
}

class ChatRequestError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

async function request(path, options, timeout) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(path, { ...options, signal: controller.signal });
    const data = await response.json();
    if (!response.ok) {
      throw new ChatRequestError(data.error?.code, data.error?.message);
    }
    return data;
  } finally {
    clearTimeout(timer);
  }
}

function explain(error, timeoutText) {
  if (error.name === "AbortError") return timeoutText;
  if (error instanceof ChatRequestError && error.message) return error.message;
  return "Could not reach the chat service. Try again.";
}

function appendMessage(role, text) {
  welcome.hidden = true;
  const item = document.createElement("li");
  item.className = `message ${role === "Coach" ? "coach" : "assistant"}`;
  const label = document.createElement("strong");
  label.textContent = role;
  const content = document.createElement("p");
  content.textContent = text;
  item.append(label, content);
  messages.append(item);
  transcript.scrollTop = transcript.scrollHeight;
}

async function initialize() {
  const current = page;
  current.busy = true;
  updateControls();
  statusLine.textContent = "Connecting…";
  errorLine.textContent = "";
  try {
    const result = await request(CONVERSATIONS, { method: "POST" }, CREATE_TIMEOUT);
    current.id = result.conversation_id;
    if (current !== page) release(current.id);
  } catch (error) {
    if (current === page) {
      errorLine.textContent = explain(error, "Connecting took too long. Try again.");
    }
  } finally {
    current.busy = false;
    if (current === page) {
      statusLine.textContent = "";
      updateControls();
    }
  }
}

async function sendTurn(turn) {
  const current = page;
  current.busy = true;
  updateControls();
  errorLine.textContent = "";
  statusLine.textContent = "Waiting for a reply…";
  try {
    const result = await request(
      `${CONVERSATIONS}/${current.id}/turns`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(turn),
      },
      TURN_TIMEOUT,
    );
    if (current === page) {
      current.failed = null;
      appendMessage("Assistant", result.reply);
    }
  } catch (error) {
    if (current === page) {
      current.failed = turn;
      if (error.code === "conversation_missing") {
        current.id = null;
        current.needsFreshContext = true;
      }
      errorLine.textContent = explain(error, "The reply took too long. Try again.");
    }
  } finally {
    current.busy = false;
    if (current === page) {
      statusLine.textContent = "";
      updateControls();
    }
  }
}

composer.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = message.value.trim();
  if (!text || page.busy || !page.id) return;
  const turn = { request_id: crypto.randomUUID(), message: text };
  appendMessage("Coach", text);
  message.value = "";
  message.focus();
  void sendTurn(turn);
});

retry.addEventListener("click", async () => {
  const current = page;
  if (current.busy) return;
  message.focus();
  if (!current.id) {
    await initialize();
    if (current !== page || !current.id) return;
    current.needsFreshContext = false;
  }
  if (current.failed) await sendTurn(current.failed);
});

function release(id) {
  if (!id) return;
  void fetch(`${CONVERSATIONS}/${id}`, { method: "DELETE", keepalive: true }).catch(() => {});
}

function resetConversation() {
  const id = page.id;
  page = newPage();
  messages.replaceChildren();
  welcome.hidden = false;
  transcript.scrollTop = 0;
  composer.reset();
  release(id);
  void initialize();
}

newChat.addEventListener("click", () => {
  if (page.busy || !page.id) return;
  message.focus();
  resetConversation();
});

for (const prompt of welcome.querySelectorAll("[data-prompt]")) {
  prompt.addEventListener("click", () => {
    const text = prompt.dataset.prompt;
    const placeholder = prompt.dataset.replace;
    message.value = text;
    message.focus();
    const start = placeholder ? text.indexOf(placeholder) : text.length;
    message.setSelectionRange(start, start + (placeholder?.length ?? 0));
  });
}

window.addEventListener("pagehide", () => {
  const id = page.id;
  page = newPage();
  page.busy = true;
  updateControls();
  release(id);
});

window.addEventListener("pageshow", (event) => {
  if (event.persisted) resetConversation();
});

void initialize();

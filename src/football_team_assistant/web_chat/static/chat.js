import { renderReply } from "/assets/chat-reply.js";
import { icon, pageHref, renderSidebar } from "/assets/shell.js";

const CONVERSATIONS = "/chat/conversations";
const CREATE_TIMEOUT = 10_000;
const TURN_TIMEOUT = 95_000;
const composer = document.querySelector("#composer");
const message = document.querySelector("#message");
const send = document.querySelector("#send");
const transcript = document.querySelector("#transcript");
const messages = document.querySelector("#messages");
const statusLine = document.querySelector("#status");
const replyBall = document.querySelector("#reply-ball");
const errorLine = document.querySelector("#error");
const errorNotice = document.querySelector("#error-notice");
const retry = document.querySelector("#retry");
const welcome = document.querySelector("#welcome");
const newChat = document.querySelector("#new-chat");
const connection = document.querySelector("#connection");
const quickActions = {
  fixtures: ["Upcoming fixtures", "calendar-days", "Which fixtures are upcoming?"],
  availability: ["Available players", "users", "Who is available for the match against opponent name?"],
  squads: ["Create squads", "waypoints", "Create balanced squads for the match against opponent name."],
  goalkeepers: [
    "GK rotation", "hand",
    "Create balanced squads for the match against opponent name, using goalkeeper rotation.",
  ],
};
const timeLabel = new Intl.DateTimeFormat("en-IE", { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
const sidebar = renderSidebar("chat");

function newPage() {
  return { id: null, busy: false, failed: null, needsFreshContext: false };
}

let page = newPage();

function updateControls() {
  send.disabled = page.busy || !page.id;
  newChat.disabled = page.busy || !page.id;
  errorNotice.hidden = !errorLine.textContent;
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

function isNearLatestMessage() {
  return transcript.scrollHeight - transcript.scrollTop - transcript.clientHeight < 32;
}

function appendMessage(role, text) {
  const isCoach = role === "Coach";
  const shouldScroll = isCoach || isNearLatestMessage();
  welcome.hidden = true;
  const item = document.createElement("li");
  item.className = `message ${isCoach ? "coach" : "assistant"}`;
  const avatar = document.createElement("span");
  avatar.className = "avatar";
  avatar.setAttribute("aria-hidden", "true");
  if (isCoach) {
    avatar.append(icon("user-round"));
  } else {
    const image = document.createElement("img");
    image.src = "/assets/clipboard.png";
    image.alt = "";
    avatar.append(image);
  }

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  const label = document.createElement("strong");
  label.className = "message-label";
  label.textContent = role;
  const content = document.createElement(isCoach ? "p" : "div");
  content.className = "message-content";
  if (isCoach) content.textContent = text;
  else content.append(renderReply(text || "The assistant returned an empty reply."));
  const timestamp = document.createElement("time");
  const now = new Date();
  timestamp.className = "message-time";
  timestamp.dateTime = now.toISOString();
  timestamp.textContent = timeLabel.format(now);
  bubble.append(label, content, timestamp);
  if (isCoach) item.append(bubble, avatar);
  else item.append(avatar, bubble);
  messages.append(item);
  if (shouldScroll) transcript.scrollTop = transcript.scrollHeight;
}

async function initialize() {
  const current = page;
  current.busy = true;
  updateControls();
  replyBall.hidden = true;
  statusLine.textContent = "Connecting…";
  errorLine.textContent = "";
  errorNotice.hidden = true;
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
  const shouldScroll = isNearLatestMessage();
  current.busy = true;
  updateControls();
  errorLine.textContent = "";
  errorNotice.hidden = true;
  replyBall.hidden = false;
  statusLine.textContent = "Gathering information…";
  if (shouldScroll) transcript.scrollTop = transcript.scrollHeight;
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
      appendMessage("Football Assistant", result.reply);
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
      replyBall.hidden = true;
      statusLine.textContent = "";
      updateControls();
    }
  }
}

message.addEventListener("keydown", (event) => {
  if (
    event.key !== "Enter" || event.shiftKey || event.isComposing || event.keyCode === 229 ||
    event.ctrlKey || event.metaKey || event.altKey
  ) return;
  event.preventDefault();
  if (!event.repeat && !send.disabled) composer.requestSubmit();
});

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

function selectPrompt(action) {
  if (!Object.hasOwn(quickActions, action)) return;
  const [, , text] = quickActions[action];
  const placeholder = "opponent name";
  const start = text.indexOf(placeholder);
  message.value = text;
  message.focus();
  message.setSelectionRange(start < 0 ? text.length : start, start < 0 ? text.length : start + placeholder.length);
}

const prompts = document.querySelector("#prompts");
for (const [action, [label, symbol]] of Object.entries(quickActions)) {
  const control = document.createElement("button");
  control.type = "button";
  control.className = "prompt secondary";
  control.append(icon(symbol), label);
  control.addEventListener("click", () => selectPrompt(action));
  prompts.append(control);
}
const ratings = document.createElement("a");
ratings.className = "prompt button secondary";
ratings.href = pageHref("ratings");
ratings.append(icon("chart-no-axes-column"), "Player ratings");
prompts.append(ratings);

document.querySelector(".sidebar nav").addEventListener("click", (event) => {
  const link = event.target.closest("[data-chat-action]");
  if (!link || event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  sidebar.closeMenu();
  selectPrompt(link.dataset.chatAction);
});

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
selectPrompt(new URL(location.href).searchParams.get("action"));

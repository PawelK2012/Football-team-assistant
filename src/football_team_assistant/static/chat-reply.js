import MarkdownIt from "./markdown-it.min.js";
import { icon } from "./shell.js";

const markdown = new MarkdownIt({ html: false, breaks: true });
markdown.renderer.rules.image = (tokens, index) => markdown.utils.escapeHtml(tokens[index].content);

const dateLabel = new Intl.DateTimeFormat("en-IE", {
  weekday: "short", day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
});

function fixtureCard(date, opponent, venue) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !opponent) return null;
  const matchDay = new Date(date + "T00:00:00Z");
  if (Number.isNaN(matchDay.valueOf()) || matchDay.toISOString().slice(0, 10) !== date) return null;

  const card = document.createElement("div");
  card.className = "fixture-card";
  const dateGroup = document.createElement("div");
  dateGroup.className = "fixture-date";
  const time = document.createElement("time");
  time.dateTime = date;
  time.textContent = dateLabel.format(matchDay);
  dateGroup.append(icon("calendar-days"), time);

  const opponentGroup = document.createElement("div");
  opponentGroup.className = "fixture-opponent";
  const label = document.createElement("div");
  const name = document.createElement("strong");
  name.textContent = opponent;
  label.append(name);
  if (venue) {
    const designation = document.createElement("span");
    designation.textContent = venue;
    label.append(designation);
  }
  opponentGroup.append(icon("shield"), label);
  card.append(dateGroup, opponentGroup);
  return card;
}

function fixtureTable(table) {
  const headers = [...table.tHead.rows[0].cells].map((cell) => cell.textContent.trim().toLowerCase());
  const dateIndex = headers.indexOf("date");
  const opponentIndex = headers.indexOf("opponent");
  const venueIndex = headers.findIndex((name) => ["venue", "home", "home/away", "home / away"].includes(name));
  if (dateIndex < 0 || opponentIndex < 0 || headers.length !== (venueIndex < 0 ? 2 : 3)) return null;

  const rows = [...table.tBodies[0].rows];
  const cards = rows.map((row) => {
    if ([...row.cells].some((cell) => cell.childElementCount)) return null;
    const values = [...row.cells].map((cell) => cell.textContent.trim());
    const location = values[venueIndex]?.toLowerCase();
    const venue = { home: "Home", away: "Away", true: "Home", false: "Away" }[location];
    if (location && !["home", "away", "true", "false"].includes(location)) return null;
    return fixtureCard(values[dateIndex], values[opponentIndex], venue);
  });
  if (!cards.length || cards.some((card) => !card)) return null;

  const group = document.createElement("div");
  group.className = "fixture-cards";
  group.append(...cards);
  return group;
}

function hasTwoSquads(content) {
  const squadLabels = [...content.children]
    .filter((element) => element.tagName === "OL")
    .map((list) => /^Squad ([AB]) \(\d+ players?\)$/.exec(
      list.previousElementSibling?.firstChild?.textContent ?? "",
    )?.[1]);
  return squadLabels.includes("A") && squadLabels.includes("B");
}

function squadCopyAction(text) {
  const action = document.createElement("div");
  action.className = "squad-copy actions";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "secondary";
  button.append(icon("copy"), "Copy squads");
  const status = document.createElement("span");
  status.setAttribute("role", "status");
  button.addEventListener("click", async () => {
    status.removeAttribute("data-error");
    status.textContent = "";
    try {
      await navigator.clipboard.writeText(text);
      status.textContent = "Copied to clipboard.";
    } catch {
      status.setAttribute("data-error", "");
      status.textContent = "Copy failed. Try again.";
    }
  });
  action.append(button, status);
  return action;
}

export function renderReply(text) {
  const block = /^Fixture: ([^\r\n]+)\r?\nDate: (\d{4}-\d{2}-\d{2})(?:\r?\n){2}/.exec(text);
  const card = block && fixtureCard(block[2], block[1].trim());

  const template = document.createElement("template");
  template.innerHTML = markdown.render(card ? text.slice(block[0].length) : text);
  for (const code of template.content.querySelectorAll("pre")) {
    code.tabIndex = 0;
  }
  for (const table of template.content.querySelectorAll("table")) {
    const cards = table.tHead?.rows.length && table.tBodies.length && fixtureTable(table);
    if (cards) {
      table.replaceWith(cards);
    } else {
      const scrollArea = document.createElement("div");
      scrollArea.className = "table-scroll";
      scrollArea.tabIndex = 0;
      scrollArea.setAttribute("role", "region");
      scrollArea.setAttribute("aria-label", "Table in reply");
      table.replaceWith(scrollArea);
      scrollArea.append(table);
    }
  }
  if (card) template.content.prepend(card);
  if (hasTwoSquads(template.content)) template.content.append(squadCopyAction(text));
  return template.content;
}

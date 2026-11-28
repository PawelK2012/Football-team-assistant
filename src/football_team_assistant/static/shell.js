const SVG = "http://www.w3.org/2000/svg";

export function icon(name) {
  const svg = document.createElementNS(SVG, "svg");
  const use = document.createElementNS(SVG, "use");
  use.setAttribute("href", `/assets/icons.svg#${name}`);
  svg.classList.add("icon");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  svg.append(use);
  return svg;
}

export const pages = {
  chat: { label: "Chat", icon: "message-circle", path: "/chat" },
  players: { label: "Players", icon: "users", path: "/admin/players" },
  fixtures: { label: "Fixtures", icon: "calendar-days", path: "/admin/fixtures" },
  availability: { label: "Availability", icon: "users", path: "/admin/availability" },
  squads: { label: "Squads", icon: "waypoints", path: "/chat?action=squads", action: true },
  goalkeepers: {
    label: "Goalkeeper Rotation", icon: "hand", path: "/chat?action=goalkeepers", action: true,
  },
  ratings: { label: "Ratings", icon: "chart-no-axes-column", path: "/admin/players?view=ratings" },
};

export function pageHref(page) {
  const path = pages[page].path;
  const chatDestination = path.startsWith("/chat");
  const inChat = document.body.dataset.app === "chat";
  if (inChat === chatDestination) return path;
  return `http://127.0.0.1:${chatDestination ? "8001" : "8002"}${path}`;
}

export function renderSidebar(currentPage) {
  const sidebar = document.querySelector(".sidebar");
  const nav = sidebar.querySelector("nav");
  sidebar.querySelector(".brand").href = pageHref("chat");
  for (const [page, details] of Object.entries(pages)) {
    const link = document.createElement("a");
    link.href = pageHref(page);
    link.append(icon(details.icon), details.label);
    if (page === currentPage) link.setAttribute("aria-current", "page");
    if (details.action) link.dataset.chatAction = page;
    nav.append(link);
  }

  const menu = sidebar.querySelector(".menu-toggle");
  const setExpanded = (expanded) => {
    menu.setAttribute("aria-expanded", String(expanded));
    menu.setAttribute("aria-label", expanded ? "Close navigation" : "Open navigation");
    menu.replaceChildren(icon(expanded ? "x" : "menu"));
  };

  menu.addEventListener("click", () => setExpanded(menu.getAttribute("aria-expanded") === "false"));
  sidebar.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || menu.getAttribute("aria-expanded") === "false") return;
    setExpanded(false);
    menu.focus();
  });
  return { closeMenu: () => setExpanded(false) };
}

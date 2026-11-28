import { icon, pages, renderSidebar } from "/assets/shell.js";

const title = document.querySelector("#page-title");
const content = document.querySelector("#content");
const status = document.querySelector("#status");
const newRecord = document.querySelector("#new-record");
const dialog = document.querySelector("#dialog");
const page = location.pathname.split("/").at(-1);
const isRatings = page === "players" && new URL(location.href).searchParams.get("view") === "ratings";

function element(tag, options = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(options)) {
    node.setAttribute(name, value);
  }
  node.append(...children);
  return node;
}

function button(label, action, style = "") {
  const control = element("button", { type: "button", class: style }, label);
  control.addEventListener("click", action);
  return control;
}

function report(message = "", isError = false) {
  status.toggleAttribute("data-error", isError);
  status.textContent = message;
}

class RequestError extends Error {
  constructor(message, code, fields = {}) {
    super(message);
    this.code = code;
    this.fields = fields;
  }
}

async function request(path, method = "GET", payload) {
  const writing = method !== "GET";
  const unknown = () => new RequestError(
    "The save could not be confirmed. Reload saved data before trying again.",
    "outcome_unknown",
  );
  const unreadable = () => new RequestError("Saved data is unavailable. Try again.", "read_failed");
  try {
    const response = await fetch("/admin/api" + path, {
      method,
      headers: writing ? { "Content-Type": "application/json" } : {},
      body: writing ? JSON.stringify(payload) : undefined,
      signal: AbortSignal.timeout(15000),
    });
    if (response.status === 204) return;
    const data = await response.json();
    if (!response.ok) {
      if (data.error) throw new RequestError(data.error.message, data.error.code, data.error.fields);
      throw writing ? unknown() : unreadable();
    }
    return data;
  } catch (error) {
    if (error instanceof RequestError) throw error;
    throw writing ? unknown() : unreadable();
  }
}

function needsReload(error) {
  return error.code === "outcome_unknown" || error.code === "record_missing";
}

function emptyPanel(message, link, label) {
  const panel = element("p", { class: "panel empty" }, message);
  if (link) panel.append(" ", element("a", { href: link }, label));
  return panel;
}

function labelFor(record, label, duplicates) {
  return duplicates.has(label) ? label + " · #" + record.id : label;
}

function duplicateLabels(records, label) {
  const seen = new Set();
  const duplicates = new Set();
  for (const record of records) {
    const value = label(record);
    if (seen.has(value)) duplicates.add(value);
    seen.add(value);
  }
  return duplicates;
}

function fixtureLabel(fixture) {
  return fixture.opponent + " · " + fixture.date + " · " + (fixture.home ? "Home" : "Away");
}

async function getFixtureRoster(fixtureId) {
  const result = await request("/fixtures/" + fixtureId + "/availability");
  return result.players;
}

function viewFixtureAvailability(fixtureId, fixtureName) {
  const message = element("p", { class: "form-message", role: "status" });
  const players = element("ul", { class: "available-player-list" });
  const close = button("Close", () => dialog.close(), "secondary");
  const retry = button("Retry", () => {
    close.focus();
    void loadPlayers();
  }, "secondary");
  const manage = element("a", {
    class: "button secondary",
    href: "/admin/availability?fixture=" + fixtureId,
  }, "Manage availability");

  async function loadPlayers() {
    retry.hidden = true;
    message.removeAttribute("data-error");
    message.textContent = "Loading availability…";
    try {
      const roster = await getFixtureRoster(fixtureId);
      const available = roster.filter((player) => player.available === true);
      if (!available.length) {
        message.textContent = "No players are marked available for this fixture.";
        return;
      }
      const duplicates = duplicateLabels(roster, (player) => player.name);
      players.replaceChildren(...available.map(({ player_id, name }) =>
        element("li", {}, labelFor({ id: player_id }, name, duplicates))));
      message.textContent = available.length === 1
        ? "1 player available."
        : available.length + " players available.";
    } catch (error) {
      message.setAttribute("data-error", "");
      message.textContent = error.message;
      retry.hidden = false;
    }
  }

  dialog.querySelector("#dialog-title").textContent = "Available players";
  dialog.querySelector("#dialog-content").replaceChildren(
    element("p", { class: "detail" }, fixtureName),
    message, players, element("div", { class: "actions" }, close, manage, retry),
  );
  dialog.oncancel = null;
  void loadPlayers();
  dialog.showModal();
  close.focus();
}

const playerFields = [
  { name: "name", label: "Name", type: "text", required: true },
  { name: "rating", label: "Rating", type: "number", min: 1, max: 6, step: 0.5, required: true },
  { name: "can_play_goalkeeper", label: "Can play goalkeeper", type: "checkbox" },
];
const fixtureFields = [
  { name: "date", label: "Date", type: "date", required: true },
  { name: "opponent", label: "Opponent", type: "text", required: true },
  { name: "home", label: "Home or away", type: "select", required: true },
];

function recordPage(isPlayers) {
  const noun = isPlayers ? "player" : "fixture";
  const collection = "/" + page;
  const fields = isPlayers ? playerFields : fixtureFields;
  const list = element("div", { tabindex: "-1" });
  const formSlot = element("div");
  const name = (record) => isPlayers ? record.name : fixtureLabel(record);
  let records = [];
  let reloadNeeded = false;
  content.append(formSlot, list);

  async function refresh() {
    records = await request(collection);
    drawList();
  }

  function drawList() {
    list.replaceChildren();
    if (!records.length) {
      list.append(emptyPanel("No " + page + " yet. Use Add " + noun + " to create the first one."));
      return;
    }
    const duplicates = duplicateLabels(records, name);
    const panel = element("div", { class: "panel" });
    const displayed = isRatings ? [...records].sort((left, right) =>
      right.rating - left.rating || left.name.localeCompare(right.name) || left.id - right.id) : records;
    for (const record of displayed) {
      const displayName = labelFor(record, name(record), duplicates);
      const description = isPlayers
        ? "Rating " + Number(record.rating).toFixed(1) + (record.can_play_goalkeeper ? " · Goalkeeper eligible" : "")
        : record.date + " · " + (record.home ? "Home" : "Away") +
          (duplicates.has(name(record)) ? " · #" + record.id : "");
      const edit = button("Edit", () => openEditor(record), "secondary");
      const remove = button("Delete", () => confirmDelete(record, displayName), "secondary");
      edit.setAttribute("aria-label", "Edit " + displayName);
      remove.setAttribute("aria-label", "Delete " + displayName);
      const actions = element("div", { class: "actions" }, edit, remove);
      if (!isPlayers) {
        const view = button("View", () => viewFixtureAvailability(record.id, displayName), "secondary");
        view.setAttribute("aria-label", "View availability for " + displayName);
        actions.prepend(view);
      }
      panel.append(element("article", { class: "row record" },
        element("div", { class: "record-summary" },
          element("span", { class: "record-icon" }, icon(isPlayers ? "user-round" : "calendar-days")),
          element("div", {}, element("div", { class: "record-name" }, isPlayers ? displayName : record.opponent),
            element("p", { class: "detail" }, description))),
        actions,
      ));
    }
    list.append(panel);
  }

  function openEditor(record) {
    if (reloadNeeded) return;
    report();
    const form = element("form", { class: "panel editor", novalidate: "" });
    const message = element("p", { class: "form-message", role: "status" });
    const controls = new Map();
    form.append(element("h2", {}, (record ? "Edit " : "Add ") + noun));
    for (const field of fields) {
      const { name: key, label, type, ...attributes } = field;
      const id = "record-" + key;
      const error = element("span", { class: "field-error", id: id + "-error" });
      const input = type === "select"
        ? element("select", { id, ...attributes },
          element("option", { value: "" }, "Choose designation"),
          element("option", { value: "true" }, "Home"),
          element("option", { value: "false" }, "Away"))
        : element("input", { id, type, ...attributes });
      input.setAttribute("aria-describedby", error.id);
      if (type === "checkbox") input.checked = record?.[key] ?? false;
      else input.value = record?.[key] ?? "";
      form.append(element("label", { class: "field" + (type === "checkbox" ? " checkbox" : ""), for: id },
        label, input, error));
      controls.set(key, { input, error });
    }
    const save = element("button", { type: "submit" }, "Save " + noun);
    const cancel = button("Cancel", () => {
      formSlot.replaceChildren();
      newRecord.focus();
    }, "secondary");
    const resume = button("Resume editing", () => {
      resume.hidden = true;
      save.disabled = false;
      save.focus();
    }, "secondary");
    resume.hidden = true;
    const recover = button("Reload saved records", async () => {
      recover.disabled = true;
      try {
        await refresh();
        reloadNeeded = false;
        recover.hidden = true;
        cancel.disabled = false;
        newRecord.disabled = false;
        if (record && !records.some((item) => item.id === record.id)) {
          formMessage("This record was deleted. You can copy your edits or cancel.", true);
        } else {
          resume.hidden = false;
          formMessage("Review the saved records before resuming your edits.");
        }
        list.focus();
      } catch (error) {
        formMessage(error.message, true);
        recover.disabled = false;
      }
    }, "secondary");
    recover.hidden = true;

    function formMessage(text, error = false) {
      message.toggleAttribute("data-error", error);
      message.textContent = text;
    }

    form.append(message, element("div", { class: "actions" }, save, cancel, recover, resume));
    formSlot.replaceChildren(form);
    controls.values().next().value.input.focus();

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (save.disabled) return;
      formMessage("");
      const payload = {};
      let invalid = false;
      for (const [key, { input, error }] of controls) {
        input.removeAttribute("aria-invalid");
        error.textContent = "";
        if (!input.validity.valid || (input.required && !input.value.trim())) {
          input.setAttribute("aria-invalid", "true");
          error.textContent = input.validationMessage || "Enter a value.";
          if (!invalid) input.focus();
          invalid = true;
        }
        payload[key] = input.type === "checkbox" ? input.checked : input.value;
      }
      if (invalid) return;
      if (isPlayers) payload.rating = Number(payload.rating);
      else payload.home = payload.home === "true";
      save.disabled = true;
      cancel.disabled = true;
      newRecord.disabled = true;
      list.inert = true;
      for (const { input } of controls.values()) input.disabled = true;
      formMessage("Saving…");
      try {
        const saved = await request(record ? collection + "/" + record.id : collection,
          record ? "PUT" : "POST", payload);
        const updated = records.filter((item) => item.id !== saved.id);
        records = [...updated, saved].sort((left, right) => (
          (isPlayers ? left.name.localeCompare(right.name) : left.date.localeCompare(right.date)) ||
          left.id - right.id
        ));
        drawList();
        formSlot.replaceChildren();
        report(isPlayers ? "Player saved." : "Fixture saved.");
        status.focus();
      } catch (error) {
        formMessage(error.message, true);
        for (const [key, text] of Object.entries(error.fields)) {
          const field = controls.get(key);
          if (!field) continue;
          field.error.textContent = text;
          field.input.setAttribute("aria-invalid", "true");
        }
        if (needsReload(error)) {
          reloadNeeded = true;
          recover.hidden = false;
          recover.disabled = false;
        }
      } finally {
        save.disabled = reloadNeeded;
        cancel.disabled = reloadNeeded;
        newRecord.disabled = reloadNeeded;
        list.inert = false;
        for (const { input } of controls.values()) input.disabled = false;
      }
    });
  }

  function confirmDelete(record, displayName) {
    if (reloadNeeded) return;
    const body = dialog.querySelector("#dialog-content");
    dialog.querySelector("#dialog-title").textContent = "Delete " + noun;
    let busy = false;
    const message = element("p", { class: "form-message", role: "status" });
    const cancel = button("Cancel", () => dialog.close(), "secondary");
    const remove = button("Delete " + noun, async () => {
      busy = true;
      cancel.disabled = true;
      remove.disabled = true;
      message.textContent = "Deleting…";
      try {
        await request(collection + "/" + record.id + "/delete", "POST", { confirmed: true });
        records = records.filter((item) => item.id !== record.id);
        drawList();
        dialog.close();
        if (formSlot.firstChild) formSlot.replaceChildren();
        report(isPlayers ? "Player deleted." : "Fixture deleted.");
        status.focus();
      } catch (error) {
        message.textContent = error.message;
        message.setAttribute("data-error", "");
        if (needsReload(error)) {
          const reload = button("Reload saved records", async () => {
            reload.disabled = true;
            try {
              await refresh();
              reloadNeeded = false;
              dialog.close();
              report("Saved records reloaded. Review the list before trying the delete again.");
            } catch (readError) {
              message.textContent = readError.message;
              reload.disabled = false;
            }
          }, "secondary");
          reloadNeeded = true;
          cancel.replaceWith(reload);
          reload.focus();
        } else {
          remove.disabled = error.code === "goalkeeper_history_exists";
        }
      } finally {
        busy = false;
        cancel.disabled = false;
      }
    }, "danger");
    dialog.oncancel = (event) => {
      if (busy || reloadNeeded) event.preventDefault();
    };
    body.replaceChildren(
      element("p", {}, displayName + " and its linked availability will be removed."),
      message, element("div", { class: "actions" }, cancel, remove),
    );
    dialog.showModal();
    cancel.focus();
  }

  newRecord.replaceChildren(icon("plus"), "Add " + noun);
  newRecord.addEventListener("click", () => openEditor());
  newRecord.hidden = false;
  newRecord.disabled = true;
  report("Loading " + page + "…");
  refresh().then(() => {
    newRecord.disabled = false;
    report();
  }).catch((error) => {
    report(error.message, true);
    list.append(button("Reload " + page, () => location.reload(), "secondary"));
  });
}

function availabilityPage() {
  const select = element("select", { id: "fixture" });
  const rosterPanel = element("div");
  const edits = new Map();
  let roster = [];
  let rosterLoaded = false;
  let fixture = "";
  let loading = false;
  let saving = false;
  let loadVersion = 0;
  let reloadRequired = false;

  const save = button("Save changes", saveChanges);
  const reload = button("Reload saved statuses", reloadSaved, "secondary");
  reload.hidden = true;
  const chooser = element("label", { class: "fixture-field", for: "fixture" }, "Fixture", select);
  const toolbar = element("div", { class: "panel toolbar" }, chooser,
    element("div", { class: "actions" }, reload, save));
  content.append(toolbar, rosterPanel);
  save.disabled = true;
  select.disabled = true;

  function updateButtons() {
    save.disabled = !edits.size || saving || loading || reloadRequired;
    reload.hidden = !reloadRequired;
    reload.disabled = loading || saving;
  }

  function drawRoster() {
    const duplicates = duplicateLabels(roster, (player) => player.name);
    rosterPanel.replaceChildren();
    if (!roster.length) {
      rosterPanel.append(emptyPanel("No players yet.", "/admin/players", "Go to Players"));
      return;
    }
    const panel = element("div", { class: "panel" });
    for (const player of roster) {
      const id = player.player_id;
      const name = labelFor({ id }, player.name, duplicates);
      const current = player.available === null ? "Not recorded" : player.available ? "Available" : "Unavailable";
      const row = element("div", { class: "row availability-row" });
      const saved = element("span", { class: "selected-status" }, fixture ? "Saved · " + current : "—");
      const change = element("select", { "aria-label": "Availability for " + name },
        element("option", { value: "" }, "No change"),
        element("option", { value: "true" }, "Available"),
        element("option", { value: "false" }, "Unavailable"));
      if (edits.has(id)) change.value = String(edits.get(id));
      change.disabled = !fixture || loading || saving;
      function showEdit() {
        row.toggleAttribute("data-pending", edits.has(id));
        saved.textContent = fixture
          ? "Saved · " + current + (edits.has(id) ? " · Unsaved change" : "")
          : "—";
      }
      change.addEventListener("change", () => {
        const value = change.value === "true";
        if (change.value === "" || value === player.available) {
          change.value = "";
          edits.delete(id);
        } else {
          edits.set(id, value);
        }
        showEdit();
        updateButtons();
      });
      row.append(element("span", { class: "record-name" }, name), saved, change);
      showEdit();
      panel.append(row);
    }
    rosterPanel.append(panel);
  }

  function rosterForFixture(selected) {
    if (selected) return getFixtureRoster(selected);
    return request("/players").then((players) => players.map((player) => ({
      player_id: player.id, name: player.name, available: null,
    })));
  }

  function updateFixtureAddress() {
    const address = new URL(location.href);
    if (fixture) address.searchParams.set("fixture", fixture);
    else address.searchParams.delete("fixture");
    history.replaceState(null, "", address);
  }

  async function showFixture(selected) {
    fixture = selected;
    roster = [];
    rosterLoaded = false;
    rosterPanel.inert = false;
    updateFixtureAddress();
    reloadRequired = false;
    loading = true;
    const version = ++loadVersion;
    rosterPanel.replaceChildren();
    report("Loading roster…");
    updateButtons();
    try {
      const players = await rosterForFixture(selected);
      if (version !== loadVersion) return;
      roster = players;
      rosterLoaded = true;
      loading = false;
      drawRoster();
      report(selected ? "" : "Choose a fixture to record availability.");
    } catch (error) {
      if (version !== loadVersion) return;
      loading = false;
      reloadRequired = true;
      report(error.message, true);
    } finally {
      if (version === loadVersion) updateButtons();
    }
  }

  function canDiscard() {
    return !edits.size || window.confirm("Discard unsaved availability changes?");
  }

  select.addEventListener("change", () => {
    if (saving || !canDiscard()) {
      select.value = fixture;
      return;
    }
    edits.clear();
    void showFixture(select.value);
  });

  document.addEventListener("click", (event) => {
    const destination = event.target.closest("a[href]");
    const target = destination && new URL(destination.href).pathname;
    const sidebarLink = destination?.matches(".brand, .sidebar nav a");
    if (!sidebarLink && !["/admin/players", "/admin/fixtures"].includes(target)) {
      return;
    }
    if (saving || !canDiscard()) event.preventDefault();
  });

  async function reloadSaved() {
    const selected = fixture;
    const version = ++loadVersion;
    loading = true;
    rosterPanel.inert = true;
    updateButtons();
    try {
      const players = await rosterForFixture(selected);
      if (version !== loadVersion) return;
      const current = new Map(players.map((player) => [player.player_id, player.available]));
      let removed = false;
      for (const [id, value] of edits) {
        if (!current.has(id)) removed = true;
        if (!current.has(id) || current.get(id) === value) edits.delete(id);
      }
      roster = players;
      rosterLoaded = true;
      reloadRequired = false;
      report(removed
        ? "Saved statuses reloaded. Edits for deleted players were removed."
        : "Saved statuses reloaded. Review any remaining edits before saving.");
    } catch (error) {
      if (version !== loadVersion) return;
      if (error.code === "record_missing") {
        await reloadFixtureChoices(selected, version, error.message);
      } else report(error.message, true);
    } finally {
      if (version === loadVersion) {
        loading = false;
        rosterPanel.inert = false;
        if (rosterLoaded) drawRoster();
        updateButtons();
      }
    }
  }

  async function saveChanges() {
    if (save.disabled) return;
    saving = true;
    select.disabled = true;
    rosterPanel.inert = true;
    updateButtons();
    report("Saving availability…");
    try {
      const changes = [...edits].map(([player_id, available]) => ({ player_id, available }));
      const result = await request("/fixtures/" + fixture + "/availability", "PUT", { changes });
      const committed = new Map(result.changes.map((change) => [change.player_id, change.available]));
      for (const player of roster) {
        if (committed.has(player.player_id)) player.available = committed.get(player.player_id);
      }
      edits.clear();
      report("Availability saved.");
    } catch (error) {
      reloadRequired = needsReload(error);
      report(error.message, true);
    } finally {
      saving = false;
      select.disabled = false;
      rosterPanel.inert = false;
      drawRoster();
      updateButtons();
      (reloadRequired ? reload : status).focus();
    }
  }

  function drawFixtureChoices(fixtures) {
    const duplicates = duplicateLabels(fixtures, fixtureLabel);
    select.replaceChildren(element("option", { value: "" }, "Select a fixture"));
    for (const item of fixtures) {
      select.append(element("option", { value: item.id }, labelFor(item, fixtureLabel(item), duplicates)));
    }
  }

  async function reloadFixtureChoices(selected, version, message) {
    try {
      const fixtures = await request("/fixtures");
      if (version !== loadVersion) return;
      drawFixtureChoices(fixtures);
      select.append(element("option", { value: selected, disabled: "" }, "Deleted fixture #" + selected));
      select.value = selected;
      report(message + " Choose another fixture or clear the selection to continue.", true);
    } catch (error) {
      if (version === loadVersion) report(error.message, true);
    }
  }

  async function initialise(initial) {
    try {
      const fixtures = await request("/fixtures");
      drawFixtureChoices(fixtures);
      select.disabled = !fixtures.length;
      select.value = fixtures.some((item) => String(item.id) === initial) ? initial : "";
      await showFixture(select.value);
      if (!fixtures.length) {
        rosterPanel.prepend(emptyPanel("No fixtures yet.", "/admin/fixtures", "Go to Fixtures"));
      }
    } catch (error) {
      report(error.message, true);
      rosterPanel.replaceChildren(button("Reload Availability", () => void initialise(initial), "secondary"));
    }
  }

  report("Loading fixtures…");
  void initialise(new URL(location.href).searchParams.get("fixture"));
}

const descriptions = {
  players: "Manage your squad, player ratings and goalkeeper eligibility.",
  fixtures: "Manage match dates, opponents, and home or away designations.",
  availability: "Choose a fixture and record who can play.",
  ratings: "Review and edit squad ratings, ordered highest first.",
};
const currentPage = isRatings ? "ratings" : page;
title.textContent = pages[currentPage].label;
document.title = title.textContent + " · Football Assistant";
document.querySelector(".page-heading").prepend(icon(pages[currentPage].icon));
document.querySelector("#page-description").textContent = descriptions[currentPage];
renderSidebar(currentPage);
if (page === "availability") availabilityPage();
else recordPage(page === "players");

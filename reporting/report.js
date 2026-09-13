/* Behaviour for the standalone HTML cost report.
 *
 * Three things happen here, and nothing else: the theme toggle, the language
 * toggle, and the what-if panel that recomputes carbon and money for a different
 * country or provider.
 *
 * The data this file works on is injected by the renderer as a single JSON blob
 * in a <script type="application/json"> tag. It is read with JSON.parse, never
 * built by string concatenation. An earlier version pasted a translation table
 * into a JavaScript string literal by hand, and the first French apostrophe
 * closed the string and silently killed every toggle on the page.
 */

(function () {
  "use strict";

  var DATA = JSON.parse(document.getElementById("report-data").textContent);
  var THEME_KEY = "saggio-theme";
  var LANGUAGE_KEY = "saggio-language";

  /* --- Theme ----------------------------------------------------------- */

  function applyTheme(theme) {
    if (theme === "light" || theme === "dark") {
      document.documentElement.setAttribute("data-theme", theme);
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
    var button = document.getElementById("theme-toggle");
    if (button) {
      button.textContent = theme === "dark" ? "☀" : "☾";
      button.setAttribute(
        "aria-label",
        theme === "dark" ? "Switch to the light theme" : "Switch to the dark theme"
      );
    }
  }

  function currentTheme() {
    var stored = null;
    try { stored = localStorage.getItem(THEME_KEY); } catch (error) { stored = null; }
    if (stored) { return stored; }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function toggleTheme() {
    var next = currentTheme() === "dark" ? "light" : "dark";
    try { localStorage.setItem(THEME_KEY, next); } catch (error) { /* private mode */ }
    applyTheme(next);
  }

  /* --- Language -------------------------------------------------------- */

  function applyLanguage(code) {
    var table = DATA.i18n[code] || DATA.i18n.en || {};
    var nodes = document.querySelectorAll("[data-i18n]");
    for (var index = 0; index < nodes.length; index += 1) {
      var key = nodes[index].getAttribute("data-i18n");
      if (Object.prototype.hasOwnProperty.call(table, key)) {
        nodes[index].textContent = table[key];
      }
    }
    document.documentElement.setAttribute("lang", code);
    var picker = document.getElementById("language-picker");
    if (picker) { picker.value = code; }
  }

  function currentLanguage() {
    var stored = null;
    try { stored = localStorage.getItem(LANGUAGE_KEY); } catch (error) { stored = null; }
    if (stored && DATA.i18n[stored]) { return stored; }
    var preferred = (navigator.language || "en").slice(0, 2).toLowerCase();
    return DATA.i18n[preferred] ? preferred : "en";
  }

  /* --- What-if --------------------------------------------------------- */

  function format(value, digits) {
    if (value === null || value === undefined || !isFinite(value)) { return "—"; }
    if (value === 0) { return "0"; }
    var magnitude = Math.abs(value);
    if (magnitude < 1e-3 || magnitude >= 1e7) { return value.toExponential(2); }
    return value.toPrecision(digits || 4).replace(/\.?0+$/, "");
  }

  function recompute() {
    var countryPicker = document.getElementById("whatif-country");
    var providerPicker = document.getElementById("whatif-provider");
    if (!countryPicker || !providerPicker) { return; }

    var country = DATA.countries[countryPicker.value] || null;
    var provider = DATA.providers[providerPicker.value] || null;
    var machineEnergy = DATA.machine_energy_kwh;

    var energyOut = document.getElementById("whatif-energy");
    var carbonOut = document.getElementById("whatif-carbon");
    var moneyOut = document.getElementById("whatif-money");
    var waterOut = document.getElementById("whatif-water");

    if (machineEnergy === null || machineEnergy === undefined) {
      /* Without a measured or estimated machine energy there is nothing to
         rescale, and inventing one here would be exactly the failure the whole
         package is built to avoid. */
      energyOut.textContent = "—";
      carbonOut.textContent = "—";
      moneyOut.textContent = "—";
      waterOut.textContent = "—";
      return;
    }

    var pue = provider && provider.pue !== null ? provider.pue : null;
    var facility = pue === null ? null : machineEnergy * pue;

    energyOut.textContent = facility === null ? "—" : format(facility) + " kWh";
    carbonOut.textContent =
      facility === null || !country || country.carbon === null
        ? "—"
        : format(facility * country.carbon) + " gCO2e";
    moneyOut.textContent =
      facility === null || !country || country.price === null
        ? "—"
        : format(facility * country.price) + " USD";
    waterOut.textContent =
      provider && provider.wue !== null && provider.wue !== undefined
        ? format(machineEnergy * provider.wue) + " L"
        : "—";
  }

  /* --- Wiring ---------------------------------------------------------- */

  applyTheme(currentTheme());
  applyLanguage(currentLanguage());
  recompute();

  var themeButton = document.getElementById("theme-toggle");
  if (themeButton) { themeButton.addEventListener("click", toggleTheme); }

  var languagePicker = document.getElementById("language-picker");
  if (languagePicker) {
    languagePicker.addEventListener("change", function (event) {
      var code = event.target.value;
      try { localStorage.setItem(LANGUAGE_KEY, code); } catch (error) { /* private mode */ }
      applyLanguage(code);
    });
  }

  ["whatif-country", "whatif-provider"].forEach(function (id) {
    var node = document.getElementById(id);
    if (node) { node.addEventListener("change", recompute); }
  });
})();

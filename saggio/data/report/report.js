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
      /* The button shows what pressing it would give you, not where you are:
         a sun while the page is dark, a moon while it is light. */
      button.textContent = theme === "dark" ? "\ud83c\udf1e" : "\ud83c\udf1b";
      /* Translated here rather than in applyLanguage, because this label
         changes with the theme as well as with the language. */
      button.setAttribute(
        "aria-label",
        theme === "dark"
          ? translated("bar.theme.light", "Switch to the light theme")
          : translated("bar.theme.dark", "Switch to the dark theme")
      );
    }
  }

  function translated(key, fallback) {
    var table = DATA.i18n[currentLanguage()] || DATA.i18n.en || {};
    return Object.prototype.hasOwnProperty.call(table, key) ? table[key] : fallback;
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

  /* A flag is not a language — English is spoken in rather more places than
     one — but it is the signifier a reader recognises at a glance, and the
     accessible name beside it says the language in words. A code with no flag
     here falls back to its own letters rather than borrowing a wrong country. */
  var FLAGS = { fr: "\ud83c\uddeb\ud83c\uddf7", en: "\ud83c\uddec\ud83c\udde7" };

  function languageCodes() {
    var node = document.getElementById("language-toggle");
    var listed = node ? (node.getAttribute("data-languages") || "") : "";
    var codes = listed.split(",").filter(function (code) { return code; });
    return codes.length ? codes : ["en"];
  }

  function nextLanguage(from) {
    var codes = languageCodes();
    var at = codes.indexOf(from);
    return codes[(at + 1) % codes.length];
  }

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
    var toggle = document.getElementById("language-toggle");
    if (toggle) {
      /* Like the theme button: the control shows the language you would get,
         not the one you are reading. */
      var target = nextLanguage(code);
      toggle.textContent = FLAGS[target] || target.toUpperCase();
      toggle.setAttribute(
        "aria-label",
        translated("bar.language." + target, "Switch to " + target.toUpperCase())
      );
    }
    /* The bar controls carry an emoji and no words, so the textContent loop
       above never reaches their accessible names; both are set here and in
       applyTheme, whose label depends on the theme as well as the language. */
    applyTheme(currentTheme());
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
    var written;
    if (magnitude < 1e-3 || magnitude >= 1e7) {
      written = value.toExponential(2);
    } else {
      written = value.toPrecision(digits || 4).replace(/\.?0+$/, "");
    }
    /* The same rule the renderer follows: a figure is written the way the
       language in force writes it, and the separator moves between digits and
       nowhere else. These panels recompute in the browser, so the server's
       formatter cannot do it for them. A contract test renders a figure both
       ways and refuses a disagreement, because two halves of one page writing
       one number differently is worse than either convention. */
    var point = translated("number.decimal", ".");
    if (point !== ".") {
      written = written.replace(/(\d)\.(\d)/g, "$1" + point + "$2");
    }
    var group = translated("number.group", "");
    /* The whole part only, and never inside an exponent: `1.906e+04` has four
       digits after its `e` and they are not a quantity. */
    if (group && written.indexOf("e") < 0) {
      written = written.replace(/^(-?)(\d{4,})/, function (all, sign, digits) {
        return sign + digits.replace(/\B(?=(\d{3})+(?!\d))/g, group);
      });
    }
    return written;
  }

  function recompute() {
    var countryPicker = document.getElementById("whatif-country");
    var providerPicker = document.getElementById("whatif-provider");
    var machinePicker = document.getElementById("whatif-machine");
    if (!countryPicker || !providerPicker) { return; }

    var country = DATA.countries[countryPicker.value] || null;
    var provider = DATA.providers[providerPicker.value] || null;
    var machineEnergy = DATA.machine_energy_kwh;

    /* Moving the machine cursor does not rescale the energy: it recomputes it,
       because energy is runtime times power and only the power changed. And it
       changes what the figure *is*. This model's own power may be a counter
       reading; every catalogue row is a datasheet rating, so the moment one is
       chosen the readout stops being a measurement and the note says so. A
       panel that let a nameplate wear a measurement's status would be the
       worst number on the page. */
    var swapped = machinePicker && machinePicker.value ? machinePicker.value : null;
    var basis = document.getElementById("whatif-basis");
    if (swapped) {
      var half = swapped.split(":");
      var table = half[0] === "cpu" ? DATA.processors : DATA.accelerators;
      var part = table ? table[half[1]] : null;
      if (!part || DATA.runtime_s === null || DATA.runtime_s === undefined) {
        /* No runtime, or no rating for that part: there is nothing to compute
           and nothing to invent. */
        machineEnergy = null;
      } else {
        machineEnergy = (DATA.runtime_s / 3600) * (part.watts / 1000);
      }
      if (basis && part) {
        basis.textContent =
          "Recomputed in your browser for " + part.name + " at its datasheet rating of " +
          format(part.watts) + " W. That rating is estimated, not measured: these figures " +
          "are no longer this machine's, and nothing is sent anywhere.";
      }
    } else if (basis) {
      basis.textContent =
        "Recomputed in your browser from the energy this model already states. " +
        "Nothing is sent anywhere.";
    }

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

  var languageToggle = document.getElementById("language-toggle");
  if (languageToggle) {
    languageToggle.addEventListener("click", function () {
      var code = nextLanguage(currentLanguage());
      try { localStorage.setItem(LANGUAGE_KEY, code); } catch (error) { /* private mode */ }
      applyLanguage(code);
    });
  }

  ["whatif-country", "whatif-provider", "whatif-machine"].forEach(function (id) {
    var node = document.getElementById(id);
    if (node) { node.addEventListener("change", recompute); }
  });
})();

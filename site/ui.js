/* The controls of the page: the theme button, and the tabs that change the
   interface concept. */

(function () {
  "use strict";

  var root = document.documentElement;

  /* ---- Theme button. It mirrors the toggle inside the launcher. ---- */

  var button = document.getElementById("theme");
  var systemDark = window.matchMedia("(prefers-color-scheme: dark)");

  function isDark() {
    var choice = root.getAttribute("data-theme");
    if (choice) return choice === "dark";
    return systemDark.matches;
  }

  /* The label names the theme that the button gives you, and not the theme
     that you have now. */
  function label() {
    var dark = isDark();
    button.textContent = dark ? "Light" : "Dark";
    button.setAttribute("aria-label", dark ? "Use the light theme" : "Use the dark theme");
  }

  if (button) {
    label();
    button.addEventListener("click", function () {
      var next = isDark() ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try {
        localStorage.setItem("tesseract-theme", next);
      } catch (error) {
        /* The choice then lasts for this page only. */
      }
      label();
    });

    /* Follow the system while the reader makes no choice. */
    systemDark.addEventListener("change", function () {
      if (!root.getAttribute("data-theme")) label();
    });
  }

  /* ---- Tabs ----------------------------------------------------------
     One tab is reachable with the tab key. The arrow keys move between
     them. This is the pattern that the ARIA practices describe.
     -------------------------------------------------------------------- */

  var tabs = Array.prototype.slice.call(document.querySelectorAll(".tab"));

  function select(tab) {
    tabs.forEach(function (other) {
      var panel = document.getElementById(other.getAttribute("aria-controls"));
      var on = other === tab;
      other.setAttribute("aria-selected", on ? "true" : "false");
      other.tabIndex = on ? 0 : -1;
      panel.classList.toggle("is-active", on);
      panel.hidden = !on;
    });
  }

  tabs.forEach(function (tab, index) {
    tab.tabIndex = tab.getAttribute("aria-selected") === "true" ? 0 : -1;

    tab.addEventListener("click", function () {
      select(tab);
    });

    tab.addEventListener("keydown", function (event) {
      var step = 0;
      if (event.key === "ArrowRight") step = 1;
      if (event.key === "ArrowLeft") step = -1;
      if (event.key === "Home") step = -index;
      if (event.key === "End") step = tabs.length - 1 - index;
      if (!step && event.key !== "Home" && event.key !== "End") return;

      event.preventDefault();
      var next = tabs[(index + step + tabs.length) % tabs.length];
      select(next);
      next.focus();
    });
  });
})();

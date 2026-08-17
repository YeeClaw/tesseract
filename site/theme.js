/* Applies the stored theme before the first paint.

   This file loads in the head, and it does not defer. A deferred script would
   run after the browser paints, and the page would flash the wrong theme. */

(function () {
  "use strict";
  try {
    var saved = localStorage.getItem("tesseract-theme");
    if (saved === "dark" || saved === "light") {
      document.documentElement.setAttribute("data-theme", saved);
    }
  } catch (error) {
    /* Private mode can refuse local storage. The system theme then wins. */
  }
})();

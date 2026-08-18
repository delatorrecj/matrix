/* MATRIX Grand Finals deck: navigation, presenter notes, progress.
   No scroll listeners, no per-frame state. Slides are shown/hidden by
   attribute; CSS owns every transition. */

(function () {
  "use strict";

  var slides = Array.prototype.slice.call(document.querySelectorAll(".slide"));
  var progress = document.querySelector(".progress");
  var notesPanel = document.querySelector(".notes-panel");
  var notesTitle = notesPanel.querySelector("[data-notes-title]");
  var notesBeat = notesPanel.querySelector("[data-notes-beat]");
  var notesBody = notesPanel.querySelector("[data-notes-body]");
  var hint = document.querySelector(".hint");

  // Slides tagged data-appendix sit outside the spoken 9 and are not counted.
  var core = slides.filter(function (s) { return !s.hasAttribute("data-appendix"); });
  var index = 0;
  var hintTimer = null;

  function render() {
    slides.forEach(function (s, i) {
      if (i === index) {
        s.setAttribute("data-active", "");
      } else {
        s.removeAttribute("data-active");
      }
    });

    var current = slides[index];
    var corePos = core.indexOf(current);
    progress.style.transform = "scaleX(" + (index + 1) / slides.length + ")";

    var counter = current.querySelector("[data-counter]");
    if (counter && corePos !== -1) {
      counter.textContent = String(corePos + 1).padStart(2, "0") + " / " + String(core.length).padStart(2, "0");
    }

    var src = current.querySelector("[data-notes]");
    notesTitle.textContent = current.getAttribute("data-title") || "";
    notesBeat.textContent = current.getAttribute("data-beat") || "Appendix, Q&A only";
    notesBody.innerHTML = src ? src.innerHTML : "<p>No notes for this slide.</p>";

    if (location.hash !== "#" + (index + 1)) {
      history.replaceState(null, "", "#" + (index + 1));
    }
  }

  function go(next) {
    var clamped = Math.max(0, Math.min(slides.length - 1, next));
    if (clamped === index) return;
    index = clamped;
    render();
  }

  document.addEventListener("keydown", function (e) {
    if (e.metaKey || e.ctrlKey || e.altKey) return;

    switch (e.key) {
      case "ArrowRight":
      case "ArrowDown":
      case "PageDown":
      case " ":
      case "Enter":
        e.preventDefault();
        go(index + 1);
        break;
      case "ArrowLeft":
      case "ArrowUp":
      case "PageUp":
      case "Backspace":
        e.preventDefault();
        go(index - 1);
        break;
      case "Home":
        e.preventDefault();
        go(0);
        break;
      case "End":
        e.preventDefault();
        go(slides.length - 1);
        break;
      case "s":
      case "S":
        e.preventDefault();
        notesPanel.toggleAttribute("data-open");
        break;
      case "f":
      case "F":
        e.preventDefault();
        if (document.fullscreenElement) {
          document.exitFullscreen();
        } else {
          document.documentElement.requestFullscreen();
        }
        break;
      default:
        break;
    }
  });

  // Click the right two thirds to advance, the left third to go back.
  // Links keep their own behaviour.
  document.addEventListener("click", function (e) {
    if (e.target.closest("a") || e.target.closest(".notes-panel")) return;
    go(e.clientX < window.innerWidth / 3 ? index - 1 : index + 1);
  });

  function showHint() {
    if (!hint) return;
    hint.removeAttribute("data-hidden");
    window.clearTimeout(hintTimer);
    hintTimer = window.setTimeout(function () {
      hint.setAttribute("data-hidden", "");
    }, 4000);
  }

  document.addEventListener("mousemove", showHint, { passive: true });

  // Demo slide: if assets/demo-still.png exists, promote the cue card to a
  // full-bleed still. Absent, the cue card stands on its own with no broken
  // image and no empty frame.
  (function () {
    var demo = document.querySelector("[data-demo-slide]");
    if (!demo) return;
    var probe = new Image();
    probe.onload = function () {
      var frame = document.createElement("div");
      frame.className = "demo-frame";
      probe.alt = "Still frame from the MATRIX scenario walkthrough.";
      frame.appendChild(probe);
      var scrim = document.createElement("div");
      scrim.className = "scrim scrim-dark";
      scrim.style.zIndex = "1";
      frame.appendChild(scrim);
      demo.insertBefore(frame, demo.firstChild);
      demo.classList.add("on-photo");
      demo.querySelector(".cue").style.position = "relative";
      demo.querySelector(".cue").style.zIndex = "2";
    };
    probe.src = "assets/demo-still.png";
  })();

  var fromHash = parseInt((location.hash || "").slice(1), 10);
  if (!isNaN(fromHash) && fromHash >= 1 && fromHash <= slides.length) {
    index = fromHash - 1;
  }

  render();
  showHint();
})();

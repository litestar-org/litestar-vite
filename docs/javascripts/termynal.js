(function () {
  "use strict";

  var TYPE_DELAY_MS = 22;
  var LINE_DELAY_MS = 260;
  var PROGRESS_STEPS = 20;
  var PROGRESS_STEP_MS = 18;

  function parseLines(rawText) {
    var lines = rawText.replace(/\r\n/g, "\n").split("\n");
    while (lines.length && !lines[lines.length - 1].trim()) {
      lines.pop();
    }
    return lines.map(function (line) {
      if (line.indexOf("$ ") === 0) {
        return { type: "input", prompt: "$", value: line.slice(2) };
      }
      if (line.indexOf("> ") === 0) {
        return { type: "input", prompt: ">", value: line.slice(2) };
      }
      if (/^--->\s*100%\s*$/.test(line.trim())) {
        return { type: "progress", value: "" };
      }
      if (line.indexOf("# ") === 0) {
        return { type: "comment", value: line };
      }
      return { type: "output", value: line };
    });
  }

  function extractCommandsOnly(items) {
    return items
      .filter(function (item) {
        return item.type === "input";
      })
      .map(function (item) {
        return item.value;
      })
      .join("\n");
  }

  function createTermynalElement(items) {
    var wrapper = document.createElement("div");
    wrapper.className = "lv-termynal";
    wrapper.setAttribute("role", "region");
    wrapper.setAttribute("aria-label", "Animated terminal session");

    var header = document.createElement("div");
    header.className = "lv-termynal__header";

    var dots = document.createElement("div");
    dots.className = "lv-termynal__dots";
    ["red", "yellow", "green"].forEach(function (color) {
      var dot = document.createElement("span");
      dot.className = "lv-termynal__dot lv-termynal__dot--" + color;
      dots.appendChild(dot);
    });

    var title = document.createElement("span");
    title.className = "lv-termynal__title";
    title.textContent = "terminal";

    var actions = document.createElement("div");
    actions.className = "lv-termynal__actions";

    var replayBtn = document.createElement("button");
    replayBtn.type = "button";
    replayBtn.className = "lv-termynal__btn";
    replayBtn.textContent = "Replay";
    replayBtn.setAttribute("aria-label", "Replay terminal animation");

    var copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "lv-termynal__btn";
    copyBtn.textContent = "Copy";
    copyBtn.setAttribute("aria-label", "Copy terminal commands");

    actions.appendChild(replayBtn);
    actions.appendChild(copyBtn);

    header.appendChild(dots);
    header.appendChild(title);
    header.appendChild(actions);

    var body = document.createElement("div");
    body.className = "lv-termynal__body";

    wrapper.appendChild(header);
    wrapper.appendChild(body);

    return {
      wrapper: wrapper,
      body: body,
      replayBtn: replayBtn,
      copyBtn: copyBtn,
    };
  }

  function sleep(ms, token) {
    return new Promise(function (resolve) {
      var timer = setTimeout(resolve, ms);
      if (token) {
        token.timers.push(timer);
      }
    });
  }

  function renderStaticLine(item) {
    var row = document.createElement("div");
    if (item.type === "input") {
      row.className = "lv-termynal__line lv-termynal__line--input";
      var promptSpan = document.createElement("span");
      promptSpan.className = "lv-termynal__prompt";
      promptSpan.textContent = item.prompt;
      var textSpan = document.createElement("span");
      textSpan.className = "lv-termynal__command";
      textSpan.textContent = item.value;
      row.appendChild(promptSpan);
      row.appendChild(textSpan);
      return row;
    }
    if (item.type === "progress") {
      row.className = "lv-termynal__line lv-termynal__line--progress";
      row.textContent = "████████████████████ 100%";
      return row;
    }
    if (item.type === "comment") {
      row.className = "lv-termynal__line lv-termynal__line--comment";
      row.textContent = item.value;
      return row;
    }
    row.className = "lv-termynal__line lv-termynal__line--output";
    if (item.value.trim().indexOf("✓") === 0) {
      row.classList.add("lv-termynal__line--success");
    }
    row.textContent = item.value || " ";
    return row;
  }

  async function runAnimation(ui, items, token) {
    ui.body.innerHTML = "";
    var reducedMotion =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reducedMotion) {
      items.forEach(function (item) {
        ui.body.appendChild(renderStaticLine(item));
      });
      return;
    }

    for (var i = 0; i < items.length; i++) {
      if (token.cancelled) {
        return;
      }
      var item = items[i];
      if (item.type === "input") {
        var row = document.createElement("div");
        row.className =
          "lv-termynal__line lv-termynal__line--input lv-termynal__line--typing";
        var promptSpan = document.createElement("span");
        promptSpan.className = "lv-termynal__prompt";
        promptSpan.textContent = item.prompt;
        var textSpan = document.createElement("span");
        textSpan.className = "lv-termynal__command";
        row.appendChild(promptSpan);
        row.appendChild(textSpan);
        ui.body.appendChild(row);

        for (var c = 0; c < item.value.length; c++) {
          if (token.cancelled) {
            return;
          }
          textSpan.textContent = item.value.slice(0, c + 1);
          await sleep(TYPE_DELAY_MS, token);
        }
        row.classList.remove("lv-termynal__line--typing");
        await sleep(LINE_DELAY_MS, token);
      } else if (item.type === "progress") {
        var progRow = document.createElement("div");
        progRow.className = "lv-termynal__line lv-termynal__line--progress";
        ui.body.appendChild(progRow);
        for (var s = 1; s <= PROGRESS_STEPS; s++) {
          if (token.cancelled) {
            return;
          }
          var filled = "█".repeat(s);
          var empty = "░".repeat(PROGRESS_STEPS - s);
          var pct = Math.round((s / PROGRESS_STEPS) * 100);
          progRow.textContent = filled + empty + " " + pct + "%";
          await sleep(PROGRESS_STEP_MS, token);
        }
        await sleep(LINE_DELAY_MS / 2, token);
      } else {
        ui.body.appendChild(renderStaticLine(item));
        await sleep(90, token);
      }
    }
  }

  function mountTermynal(targetBlock) {
    if (!targetBlock || targetBlock.dataset.lvTermynalMounted === "1") {
      return;
    }
    targetBlock.dataset.lvTermynalMounted = "1";
    var codeEl = targetBlock.querySelector("code") || targetBlock;
    var rawText = codeEl.textContent || "";
    var items = parseLines(rawText);
    if (!items.length) {
      return;
    }

    var ui = createTermynalElement(items);
    var activeToken = { cancelled: false, timers: [] };

    function start() {
      activeToken.cancelled = true;
      activeToken.timers.forEach(clearTimeout);
      activeToken = { cancelled: false, timers: [] };
      runAnimation(ui, items, activeToken);
    }

    ui.replayBtn.addEventListener("click", function () {
      start();
    });

    ui.copyBtn.addEventListener("click", function () {
      var cmdText = extractCommandsOnly(items) || rawText.trim();
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(cmdText).then(function () {
          ui.copyBtn.textContent = "Copied";
          setTimeout(function () {
            ui.copyBtn.textContent = "Copy";
          }, 1400);
        });
      }
    });

    targetBlock.parentNode.replaceChild(ui.wrapper, targetBlock);

    if ("IntersectionObserver" in window) {
      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              observer.disconnect();
              start();
            }
          });
        },
        { threshold: 0.15 }
      );
      observer.observe(ui.wrapper);
    } else {
      start();
    }
  }

  function discoverTermynalBlocks(root) {
    var scope = root || document;
    var walker = document.createTreeWalker(
      scope,
      NodeFilter.SHOW_COMMENT,
      null
    );
    var commentNodes = [];
    var current;
    while ((current = walker.nextNode())) {
      if (/^\s*termynal\b/i.test(current.nodeValue || "")) {
        commentNodes.push(current);
      }
    }

    commentNodes.forEach(function (comment) {
      var next = comment.nextSibling;
      while (next && next.nodeType !== 1) {
        next = next.nextSibling;
      }
      if (
        next &&
        (next.classList.contains("highlight") ||
          next.tagName === "PRE" ||
          next.querySelector("pre"))
      ) {
        mountTermynal(next);
      }
    });

    var explicit = scope.querySelectorAll("[data-termynal], .termynal");
    explicit.forEach(function (el) {
      mountTermynal(el);
    });
  }

  if (typeof window !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function () {
        discoverTermynalBlocks(document);
      });
    } else {
      discoverTermynalBlocks(document);
    }
    if (window.document$ && typeof window.document$.subscribe === "function") {
      window.document$.subscribe(function () {
        discoverTermynalBlocks(document);
      });
    }
  }
})();

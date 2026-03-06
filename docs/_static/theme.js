(() => {
  const root = document.documentElement
  const COPY_RESET_MS = 1600

  const markReady = () => {
    root.dataset.docsTheme = "litestar-vite"
    document.body?.setAttribute("data-docs-theme", "litestar-vite")
  }

  const normalizeLanguage = (value) => {
    if (!value) {
      return ""
    }
    return value
      .replace(/^(language-|highlight-)/, "")
      .replace(/\bnotranslate\b/g, "")
      .replace(/[-_]/g, " ")
      .trim()
      .toUpperCase()
  }

  const inferLanguage = (block) => {
    const directClass = [...block.classList].find((className) => className.startsWith("highlight-"))
    if (directClass) {
      return normalizeLanguage(directClass)
    }

    const codeClass = block.querySelector("code[class]")?.className || block.querySelector("pre")?.className || ""
    if (codeClass) {
      const languageClass = codeClass
        .split(/\s+/)
        .find((className) => className.startsWith("language-") || className.startsWith("highlight-"))
      return normalizeLanguage(languageClass || codeClass)
    }

    return "CODE"
  }

  const setTemporaryLabel = (element, label) => {
    const original = element.dataset.originalLabel || element.textContent?.trim() || "Copy"
    element.dataset.originalLabel = original
    element.textContent = label
    window.setTimeout(() => {
      element.textContent = original
      element.removeAttribute("data-copied")
    }, COPY_RESET_MS)
  }

  const decorateCopyButton = (button) => {
    if (button.dataset.lvReady === "true") {
      return
    }

    button.dataset.lvReady = "true"
    button.type = "button"
    button.setAttribute("aria-label", button.getAttribute("aria-label") || "Copy code")
    if (!button.textContent?.trim()) {
      button.textContent = "Copy"
    }
  }

  const enhanceCodeBlocks = () => {
    document.querySelectorAll("div.highlight").forEach((block) => {
      block.classList.add("lv-code-block")
      block.dataset.language = inferLanguage(block)
      block.setAttribute("data-language", block.dataset.language)
      block.querySelectorAll(".copybtn").forEach((button) => decorateCopyButton(button))
    })
  }

  const copyText = async (button, text, successLabel, failureLabel) => {
    try {
      await navigator.clipboard.writeText(text)
      button.dataset.copied = "true"
      setTemporaryLabel(button, successLabel)
    } catch {
      setTemporaryLabel(button, failureLabel)
    }
  }

  const initPageActions = () => {
    document.querySelectorAll(".copy-page-wrapper").forEach((wrapper) => {
      if (wrapper.dataset.lvReady === "true") {
        return
      }
      wrapper.dataset.lvReady = "true"

      const menuButton = wrapper.querySelector(".js-menu")
      const menu = wrapper.querySelector("#copy-page-content")
      const copyButtons = wrapper.querySelectorAll(".js-copy")

      const closeMenu = () => {
        if (!(menu instanceof HTMLElement) || !(menuButton instanceof HTMLButtonElement)) {
          return
        }
        menu.setAttribute("aria-hidden", "true")
        menuButton.setAttribute("aria-expanded", "false")
      }

      if (menu instanceof HTMLElement && menuButton instanceof HTMLButtonElement) {
        menu.setAttribute("aria-hidden", menu.getAttribute("aria-hidden") || "true")
        menuButton.setAttribute("aria-expanded", menuButton.getAttribute("aria-expanded") || "false")

        menuButton.addEventListener("click", () => {
          const expanded = menuButton.getAttribute("aria-expanded") === "true"
          menuButton.setAttribute("aria-expanded", String(!expanded))
          menu.setAttribute("aria-hidden", String(expanded))
        })

        document.addEventListener("click", (event) => {
          if (!wrapper.contains(event.target)) {
            closeMenu()
          }
        })

        document.addEventListener("keydown", (event) => {
          if (event.key === "Escape") {
            closeMenu()
          }
        })
      }

      copyButtons.forEach((button) => {
        if (!(button instanceof HTMLButtonElement)) {
          return
        }
        button.addEventListener("click", async (event) => {
          event.preventDefault()
          const url = button.dataset.url
          if (url) {
            const response = await fetch(url)
            const text = await response.text()
            await copyText(button, text, "Copied", "Failed")
          } else {
            await copyText(button, window.location.href, "Link copied", "Failed")
          }
          closeMenu()
        })
      })
    })
  }

  const boot = () => {
    markReady()
    enhanceCodeBlocks()
    initPageActions()
    window.setTimeout(() => {
      enhanceCodeBlocks()
      initPageActions()
    }, 180)
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true })
  } else {
    boot()
  }

  window.addEventListener("load", () => {
    enhanceCodeBlocks()
    initPageActions()
  }, { once: true })
})()

(() => {
  const root = document.documentElement;

  const markReady = () => {
    root.dataset.docsTheme = "litestar-vite";
    document.body?.setAttribute("data-docs-theme", "litestar-vite");
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", markReady, { once: true });
  } else {
    markReady();
  }
})();

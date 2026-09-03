document.documentElement.classList.add("js");

(() => {
  const drawer = document.querySelector("[data-mobile-menu]");
  const openButton = document.querySelector("[data-menu-open]");
  const closeButton = document.querySelector("[data-menu-close]");
  const overlay = document.querySelector("[data-menu-overlay]");
  let previousFocus = null;

  if (drawer && openButton && closeButton && overlay) {
    const focusable = () => [...drawer.querySelectorAll("a, button, input, select, [tabindex]:not([tabindex='-1'])")];
    const open = () => { previousFocus = document.activeElement; drawer.classList.add("open"); drawer.setAttribute("aria-hidden", "false"); openButton.setAttribute("aria-expanded", "true"); overlay.hidden = false; document.body.classList.add("nav-open"); closeButton.focus(); };
    const close = () => { drawer.classList.remove("open"); drawer.setAttribute("aria-hidden", "true"); openButton.setAttribute("aria-expanded", "false"); overlay.hidden = true; document.body.classList.remove("nav-open"); previousFocus?.focus(); };
    openButton.addEventListener("click", open); closeButton.addEventListener("click", close); overlay.addEventListener("click", close);
    drawer.querySelectorAll("a").forEach((link) => link.addEventListener("click", close));
    document.addEventListener("keydown", (event) => { if (!drawer.classList.contains("open")) return; if (event.key === "Escape") close(); if (event.key === "Tab") { const items = focusable(); const first = items[0]; const last = items[items.length - 1]; if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); } else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); } } });
  }

  const header = document.querySelector("[data-site-header]");
  const updateHeader = () => header?.classList.toggle("scrolled", window.scrollY > 28);
  updateHeader(); window.addEventListener("scroll", updateHeader, { passive: true });

  const revealItems = document.querySelectorAll(".reveal");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (reducedMotion.matches || !("IntersectionObserver" in window)) revealItems.forEach((item) => item.classList.add("in"));
  else { const observer = new IntersectionObserver((entries) => { entries.forEach((entry) => { if (entry.isIntersecting) { entry.target.classList.add("in"); observer.unobserve(entry.target); } }); }, { threshold: 0.08 }); revealItems.forEach((item) => observer.observe(item)); }

  const parallaxItems = document.querySelectorAll("[data-parallax]");
  if (parallaxItems.length && !reducedMotion.matches) {
    let scheduled = false;
    const updateParallax = () => { const center = window.innerHeight / 2; parallaxItems.forEach((item) => { const speed = Number(item.dataset.parallax || 0); const delta = (item.getBoundingClientRect().top - center) * speed * -0.055; item.style.translate = `0 ${Math.max(-18, Math.min(18, delta))}px`; }); scheduled = false; };
    window.addEventListener("scroll", () => { if (!scheduled) { window.requestAnimationFrame(updateParallax); scheduled = true; } }, { passive: true });
    updateParallax();
  }
})();

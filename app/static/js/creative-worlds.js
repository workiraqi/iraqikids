(() => {
  const hero = document.querySelector("[data-creative-worlds]");
  if (!hero) return;

  const eyes = [...hero.querySelectorAll("[data-eye]")];
  const worlds = [...hero.querySelectorAll("[data-world]")];
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
  const directions = ["e", "se", "s", "sw", "w", "nw", "n", "ne"];
  let blinkTimer = 0;
  let mobileGazeTimer = 0;

  const gazeForPoint = (eye, clientX, clientY) => {
    const rect = eye.getBoundingClientRect();
    const dx = clientX - (rect.left + rect.width / 2);
    const dy = clientY - (rect.top + rect.height / 2);
    if (Math.hypot(dx, dy) < 18) return "center";
    const sector = Math.round(Math.atan2(dy, dx) / (Math.PI / 4));
    return directions[(sector + 8) % 8];
  };

  const lookAt = (clientX, clientY) => {
    eyes.forEach((eye) => { eye.dataset.gaze = gazeForPoint(eye, clientX, clientY); });
  };

  const lookAtElement = (element) => {
    const rect = element.getBoundingClientRect();
    lookAt(rect.left + rect.width / 2, rect.top + rect.height / 2);
  };

  const resetGaze = () => eyes.forEach((eye) => { eye.dataset.gaze = "center"; });

  const activateWorld = (world) => {
    hero.dataset.activeWorld = world.dataset.world;
    lookAtElement(world);
  };

  worlds.forEach((world) => {
    world.addEventListener("pointerenter", () => activateWorld(world));
    world.addEventListener("focus", () => activateWorld(world));
    world.addEventListener("pointerdown", () => activateWorld(world));
    world.addEventListener("pointerleave", () => {
      if (finePointer.matches) { hero.dataset.activeWorld = "none"; resetGaze(); }
    });
    world.addEventListener("blur", () => {
      hero.dataset.activeWorld = "none";
      resetGaze();
    });
  });

  if (finePointer.matches && !reducedMotion.matches) {
    hero.addEventListener("pointermove", (event) => lookAt(event.clientX, event.clientY), { passive: true });
    hero.addEventListener("pointerleave", resetGaze);
  }

  const scheduleBlink = () => {
    if (reducedMotion.matches) return;
    blinkTimer = window.setTimeout(() => {
      hero.classList.add("is-blinking");
      window.setTimeout(() => hero.classList.remove("is-blinking"), 150);
      scheduleBlink();
    }, 3200 + Math.random() * 2800);
  };

  const startMobileGaze = () => {
    if (finePointer.matches || reducedMotion.matches) return;
    const sequence = ["center", "ne", "center", "w", "se", "center"];
    let index = 0;
    mobileGazeTimer = window.setInterval(() => {
      const gaze = sequence[index % sequence.length];
      eyes.forEach((eye) => { eye.dataset.gaze = gaze; });
      index += 1;
    }, 1800);
  };

  const stopAmbientMotion = () => {
    window.clearTimeout(blinkTimer);
    window.clearInterval(mobileGazeTimer);
    hero.classList.remove("is-blinking");
    resetGaze();
  };

  scheduleBlink();
  startMobileGaze();
  reducedMotion.addEventListener("change", (event) => {
    stopAmbientMotion();
    if (!event.matches) { scheduleBlink(); startMobileGaze(); }
  });
})();

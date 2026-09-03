(() => {
  const form = document.querySelector("[data-theme-form]");
  const preview = document.querySelector("[data-theme-preview]");
  if (!form || !preview) return;

  const apply = (input) => {
    const token = input.dataset.token.replaceAll("_", "-");
    preview.style.setProperty(`--preview-${token}`, input.value);
    const output = input.parentElement.querySelector("output");
    if (output) output.textContent = input.value;
  };

  form.querySelectorAll("input[type='color'][data-token]").forEach((input) => {
    apply(input);
    input.addEventListener("input", () => apply(input));
  });
})();

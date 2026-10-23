document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-category-select]").forEach((form) => {
    const kindSelect = form.querySelector(".kind-select");
    const categorySelect = form.querySelector(".category-select");
    if (!kindSelect || !categorySelect) return;

    const updateCategories = () => {
      const kind = kindSelect.value;
      let firstVisible = "";
      Array.from(categorySelect.options).forEach((option) => {
        if (!option.dataset.kind) return;
        const visible = option.dataset.kind === kind;
        option.hidden = !visible;
        option.disabled = !visible;
        if (visible && !firstVisible) firstVisible = option.value;
      });

      const selected = categorySelect.selectedOptions[0];
      if (!selected || selected.disabled) categorySelect.value = firstVisible;
      categorySelect.disabled = !firstVisible;
    };

    kindSelect.addEventListener("change", updateCategories);
    updateCategories();
  });

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
});

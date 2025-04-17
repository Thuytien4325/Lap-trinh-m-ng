export default function initContextMenu({ selector, items, onAction }) {
  const menu = document.createElement("div");
  menu.className = "context-menu";
  document.body.appendChild(menu);

  let currentTarget = null;

  document.addEventListener("contextmenu", (e) => {
    const target = e.target.closest(selector);
    if (!target) return;

    e.preventDefault();
    currentTarget = target;
    const fileUrl = target.getAttribute("data-url") || "";

    menu.innerHTML = "";
    items.forEach(({ action, label }) => {
      const item = document.createElement("div");
      item.className = "context-menu-item";
      item.textContent = label;
      item.onclick = () => {
        menu.style.display = "none";
        if (onAction) onAction(action, fileUrl, target);
      };
      menu.appendChild(item);
    });

    menu.style.top = e.pageY + "px";
    menu.style.left = e.pageX + "px";
    menu.style.display = "block";
  });

  document.addEventListener("click", () => {
    menu.style.display = "none";
  });
}

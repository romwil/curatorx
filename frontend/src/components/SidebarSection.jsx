import { useEffect, useId, useState } from "react";

const STORAGE_PREFIX = "curatorx.sidebar.section";

export default function SidebarSection({
  sectionId,
  title,
  icon = null,
  children,
  collapsible = true,
  defaultCollapsed = false,
  alwaysVisible = false,
  sidebarCollapsed = false,
}) {
  const storageKey = `${STORAGE_PREFIX}.${sectionId}`;
  const panelId = useId();

  const [collapsed, setCollapsed] = useState(() => {
    try {
      const stored = sessionStorage.getItem(storageKey);
      if (stored !== null) return stored === "true";
    } catch {
      // sessionStorage unavailable
    }
    return defaultCollapsed;
  });

  useEffect(() => {
    try {
      sessionStorage.setItem(storageKey, String(collapsed));
    } catch {
      // sessionStorage unavailable
    }
  }, [collapsed, storageKey]);

  const showBody = !sidebarCollapsed && (alwaysVisible || !collapsible || !collapsed);

  const headerContent = (
    <>
      {icon ? (
        <span className="sidebar-section-icon" aria-hidden="true">
          {icon}
        </span>
      ) : null}
      <span className="sidebar-section-title eyebrow">{title}</span>
      {collapsible && !alwaysVisible ? (
        <span className="sidebar-section-chevron" aria-hidden="true">
          {collapsed ? "▸" : "▾"}
        </span>
      ) : null}
    </>
  );

  return (
    <section
      className={`sidebar-section ${collapsed && collapsible ? "is-collapsed" : "is-expanded"}`}
      data-testid={`sidebar-section-${sectionId}`}
    >
      {collapsible && !alwaysVisible ? (
        <button
          type="button"
          className="sidebar-section-header"
          onClick={() => setCollapsed((value) => !value)}
          aria-expanded={!collapsed}
          aria-controls={panelId}
        >
          {headerContent}
        </button>
      ) : (
        <div className="sidebar-section-header sidebar-section-header-static">{headerContent}</div>
      )}
      {showBody ? (
        <div className="sidebar-section-body" id={panelId}>
          {children}
        </div>
      ) : null}
    </section>
  );
}

import React from "react";

export function EmptyState({
  title,
  description,
  action,
  icon,
  className = ""
}) {
  return (
    <div className={`empty-state ${className}`}>
      {icon && <div className="empty-state-icon">{icon}</div>}
      <h4 className="empty-state-title">{title}</h4>
      {description && <p className="empty-state-desc">{description}</p>}
      {action && <div>{action}</div>}
    </div>
  );
}

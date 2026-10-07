import React from "react";

export function Card({ children, className = "", style = {}, onClick, interactive = false, ...props }) {
  const classes = `card ${interactive ? "card-interactive" : ""} ${className}`.trim();
  return (
    <div className={classes} style={style} onClick={onClick} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, action, className = "" }) {
  return (
    <div className={`card-header ${className}`}>
      <div>
        {title && <h3 className="card-title">{title}</h3>}
        {subtitle && <p className="card-subtitle">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}


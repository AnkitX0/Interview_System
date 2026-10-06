import React from "react";

export function Badge({ children, variant = "neutral", className = "", style = {} }) {
  // variants: neutral, success, warning, danger, info
  const classes = `badge badge-${variant} ${className}`.trim();
  return (
    <span className={classes} style={style}>
      {children}
    </span>
  );
}

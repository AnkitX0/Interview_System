import React from "react";

export function Skeleton({ width = "100%", height = "1rem", borderRadius, className = "", style = {} }) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{
        width,
        height,
        borderRadius: borderRadius || "var(--radius-sm)",
        ...style
      }}
    />
  );
}

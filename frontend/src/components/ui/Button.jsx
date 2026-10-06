import React from "react";

export function Button({
  children,
  variant = "primary", // primary, accent, secondary, subtle, danger
  size = "md", // sm, md, lg
  fullWidth = false,
  loading = false,
  disabled = false,
  className = "",
  type = "button",
  onClick,
  ...props
}) {
  const sizeClass = size === "sm" ? "btn-sm" : size === "lg" ? "btn-lg" : "";
  const fullClass = fullWidth ? "btn-full" : "";
  const classes = `btn btn-${variant} ${sizeClass} ${fullClass} ${className}`.trim();

  return (
    <button
      type={type}
      className={classes}
      disabled={disabled || loading}
      onClick={onClick}
      {...props}
    >
      {loading ? (
        <>
          <span
            style={{
              display: "inline-block",
              width: "14px",
              height: "14px",
              border: "2px solid currentColor",
              borderRightColor: "transparent",
              borderRadius: "50%",
              animation: "spin 0.6s linear infinite"
            }}
          />
          <span>Loading...</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}


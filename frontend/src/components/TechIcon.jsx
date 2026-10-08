import React from "react";

// Bundled clean SVG icons for programming languages and engineering tools (No external network fetching)
export function TechIcon({ name = "", size = 16, className = "" }) {
  const norm = (name || "").toLowerCase().trim();

  // Python
  if (norm.includes("python") || norm === "py") {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <path d="M11.9 2C6.7 2 7 4.2 7 4.2V6.5H12.2V7.3H3.6C3.6 7.3 1 7 1 12.1C1 17.3 3.3 17 3.3 17H5V14.6C5 11.8 7.3 11.9 7.3 11.9H12.2C14.7 11.9 14.5 9.7 14.5 9.7V4.2C14.5 4.2 14.8 2 11.9 2ZM9.5 3.4C10 3.4 10.4 3.8 10.4 4.3C10.4 4.8 10 5.2 9.5 5.2C9 5.2 8.6 4.8 8.6 4.3C8.6 3.8 9 3.4 9.5 3.4Z" fill="#387EB8"/>
        <path d="M12.1 22C17.3 22 17 19.8 17 19.8V17.5H11.8V16.7H20.4C20.4 16.7 23 17 23 11.9C23 6.7 20.7 7 20.7 7H19V9.4C19 12.2 16.7 12.1 16.7 12.1H11.8C9.3 12.1 9.5 14.3 9.5 14.3V19.8C9.5 19.8 9.2 22 12.1 22ZM14.5 20.6C14 20.6 13.6 20.2 13.6 19.7C13.6 19.2 14 18.8 14.5 18.8C15 18.8 15.4 19.2 15.4 19.7C15.4 20.2 15 20.6 14.5 20.6Z" fill="#FFE873"/>
      </svg>
    );
  }

  // JavaScript
  if (norm.includes("javascript") || norm === "js") {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <rect width="24" height="24" rx="4" fill="#F7DF1E"/>
        <path d="M7 17.5V10H9V15.5C9 16.8 8.2 17.5 7 17.5ZM13.5 17.5C11.5 17.5 10.5 16.4 10.5 15.2L12.3 14.2C12.6 14.8 13.1 15.6 14.1 15.6C14.9 15.6 15.4 15.2 15.4 14.6C15.4 13.9 14.8 13.6 13.8 13.1L13.2 12.8C11.8 12.1 10.9 11.3 10.9 9.8C10.9 8.2 12.2 7 14 7C15.4 7 16.5 7.6 17.1 8.8L15.4 9.9C15.1 9.4 14.6 9 14 9C13.4 9 12.9 9.3 12.9 9.8C12.9 10.4 13.4 10.6 14.2 11L14.8 11.3C16.5 12.1 17.5 12.9 17.5 14.6C17.5 16.3 16 17.5 13.5 17.5Z" fill="#000000"/>
      </svg>
    );
  }

  // TypeScript
  if (norm.includes("typescript") || norm === "ts") {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <rect width="24" height="24" rx="4" fill="#3178C6"/>
        <path d="M5 9H11V11H9V17H7V11H5V9ZM13.5 17.2C11.8 17.2 11 16.2 11 15.1L12.7 14.2C13 14.8 13.4 15.5 14.2 15.5C14.9 15.5 15.3 15.2 15.3 14.7C15.3 14.1 14.8 13.8 13.9 13.4L13.4 13.2C12.2 12.6 11.4 11.9 11.4 10.6C11.4 9.2 12.5 8.2 14.1 8.2C15.3 8.2 16.2 8.7 16.8 9.7L15.3 10.7C15 10.3 14.6 9.9 14.1 9.9C13.6 9.9 13.2 10.2 13.2 10.6C13.2 11.1 13.6 11.3 14.3 11.6L14.8 11.8C16.3 12.5 17.1 13.2 17.1 14.7C17.1 16.2 15.8 17.2 13.5 17.2Z" fill="#FFFFFF"/>
      </svg>
    );
  }

  // Java
  if (norm.includes("java") && !norm.includes("javascript")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <path d="M9 19C13 20 16 19 19 18C16 21 11 21 7 20C6 19.5 7.5 19 9 19Z" fill="#E76F00"/>
        <path d="M7 16C12 17 16 16 20 15C17 18 10 18 5 17C4.5 16.5 5.5 16 7 16Z" fill="#5382A1"/>
        <path d="M12 2C10 5 8 7 11 10C13 12 15 14 12 17C14 15 16 13 14 10C12 7 14 5 12 2Z" fill="#E76F00"/>
      </svg>
    );
  }

  // C++ / Cpp
  if (norm.includes("c++") || norm.includes("cpp")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <rect width="24" height="24" rx="4" fill="#00599C"/>
        <path d="M8.5 7C5.5 7 4 9 4 12C4 15 5.5 17 8.5 17C10 17 11.5 16.2 12 15.2L10.5 14.2C10 14.8 9.2 15.2 8.5 15.2C6.8 15.2 5.8 13.8 5.8 12C5.8 10.2 6.8 8.8 8.5 8.8C9.2 8.8 10 9.2 10.5 9.8L12 8.8C11.5 7.8 10 7 8.5 7ZM14 11V9H15V11H17V12H15V14H14V12H12V11H14ZM18 11V9H19V11H21V12H19V14H18V12H16V11H18Z" fill="#FFFFFF"/>
      </svg>
    );
  }

  // C
  if (norm === "c" || norm.startsWith("c lang")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <rect width="24" height="24" rx="4" fill="#A8B9CC"/>
        <path d="M14 6C9 6 7 8.5 7 12C7 15.5 9 18 14 18C16.5 18 18.5 17 19.5 15.5L17.5 14C16.8 15 15.5 16 14 16C10.5 16 9.2 14 9.2 12C9.2 10 10.5 8 14 8C15.5 8 16.8 9 17.5 10L19.5 8.5C18.5 7 16.5 6 14 6Z" fill="#1C2D44"/>
      </svg>
    );
  }

  // Go / Golang
  if (norm.includes("go") || norm.includes("golang")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <rect width="24" height="24" rx="4" fill="#00ADD8"/>
        <path d="M6 10H10V11.5H7.5V14.5H10.5V13H9V11.8H12V16H6V10ZM13 10H18C18.5 10 19 10.5 19 11V15C19 15.5 18.5 16 18 16H13C12.5 16 12 15.5 12 15V11C12 10.5 12.5 10 13 10ZM13.5 11.5V14.5H17.5V11.5H13.5Z" fill="#FFFFFF"/>
      </svg>
    );
  }

  // Rust
  if (norm.includes("rust")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <circle cx="12" cy="12" r="10" fill="#DEA584"/>
        <path d="M12 4C7.6 4 4 7.6 4 12C4 16.4 7.6 20 12 20C16.4 20 20 16.4 20 12C20 7.6 16.4 4 12 4ZM10 8H14C15.1 8 16 8.9 16 10C16 11.1 15.1 12 14 12H12V16H10V8Z" fill="#000000"/>
      </svg>
    );
  }

  // SQL / PostgreSQL / MySQL / SQLite
  if (norm.includes("sql") || norm.includes("postgres") || norm.includes("mysql") || norm.includes("sqlite")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <ellipse cx="12" cy="6" rx="8" ry="3" fill="#336791"/>
        <path d="M4 6V12C4 13.7 7.6 15 12 15C16.4 15 20 13.7 20 12V6" stroke="#255173" strokeWidth="2" fill="none"/>
        <path d="M4 12V18C4 19.7 7.6 21 12 21C16.4 21 20 19.7 20 18V12" stroke="#255173" strokeWidth="2" fill="none"/>
      </svg>
    );
  }

  // React
  if (norm.includes("react")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <ellipse cx="12" cy="12" rx="9" ry="3.5" transform="rotate(30 12 12)" stroke="#61DAFB" strokeWidth="1.5"/>
        <ellipse cx="12" cy="12" rx="9" ry="3.5" transform="rotate(90 12 12)" stroke="#61DAFB" strokeWidth="1.5"/>
        <ellipse cx="12" cy="12" rx="9" ry="3.5" transform="rotate(150 12 12)" stroke="#61DAFB" strokeWidth="1.5"/>
        <circle cx="12" cy="12" r="2" fill="#61DAFB"/>
      </svg>
    );
  }

  // FastAPI
  if (norm.includes("fastapi")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <circle cx="12" cy="12" r="10" fill="#059669"/>
        <path d="M13 4L6 14H12L11 20L18 10H12L13 4Z" fill="#FFFFFF"/>
      </svg>
    );
  }

  // Docker
  if (norm.includes("docker")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <path d="M3 13C4 13 5 14 7 14C9 14 11 13 13 13C15 13 17 14 19 14C20 14 21 13.5 22 13C22 18 18 20 12 20C6 20 2 18 3 13Z" fill="#2496ED"/>
        <rect x="7" y="10" width="2" height="2" fill="#2496ED"/>
        <rect x="10" y="10" width="2" height="2" fill="#2496ED"/>
        <rect x="13" y="10" width="2" height="2" fill="#2496ED"/>
        <rect x="10" y="7" width="2" height="2" fill="#2496ED"/>
        <rect x="13" y="7" width="2" height="2" fill="#2496ED"/>
      </svg>
    );
  }

  // Git / GitHub
  if (norm.includes("git")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <circle cx="6" cy="6" r="3" fill="#F05032"/>
        <circle cx="6" cy="18" r="3" fill="#F05032"/>
        <circle cx="18" cy="9" r="3" fill="#F05032"/>
        <path d="M6 9V15M6 9L18 9" stroke="#F05032" strokeWidth="2"/>
      </svg>
    );
  }

  // PyTorch / AI / ML
  if (norm.includes("pytorch") || norm.includes("torch")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <circle cx="12" cy="12" r="9" stroke="#EE4C2C" strokeWidth="2"/>
        <path d="M12 6V11L15 9" stroke="#EE4C2C" strokeWidth="2" strokeLinecap="round"/>
        <circle cx="15.5" cy="8.5" r="1.5" fill="#EE4C2C"/>
      </svg>
    );
  }

  // Redis
  if (norm.includes("redis")) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
        <rect width="24" height="24" rx="4" fill="#DC382D"/>
        <path d="M5 9L12 6L19 9L12 12L5 9Z" fill="#FFFFFF"/>
        <path d="M5 12L12 15L19 12" stroke="#FFFFFF" strokeWidth="1.5"/>
        <path d="M5 15L12 18L19 15" stroke="#FFFFFF" strokeWidth="1.5"/>
      </svg>
    );
  }

  // Generic Chip / Technology Fallback (No random emoji, clean SVG asset)
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
      <rect x="5" y="5" width="14" height="14" rx="2" stroke="currentColor" strokeWidth="1.8"/>
      <path d="M9 2V5M15 2V5M9 19V22M15 19V22M2 9H5M2 15H5M19 9H22M19 15H22" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
      <rect x="9" y="9" width="6" height="6" rx="1" fill="currentColor" fillOpacity="0.3"/>
    </svg>
  );
}
export default TechIcon;

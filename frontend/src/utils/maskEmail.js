/**
 * Masks an email address for privacy display.
 * e.g., "candidate@gmail.com" -> "ca*****e@gmail.com"
 */
export function maskEmail(email) {
  if (!email || !email.includes("@")) return email || "";
  const [localPart, domain] = email.split("@");
  if (localPart.length <= 2) {
    return `${localPart[0]}***@${domain}`;
  }
  const visiblePrefix = localPart.slice(0, 2);
  const visibleSuffix = localPart.slice(-1);
  return `${visiblePrefix}${"*".repeat(Math.max(3, localPart.length - 3))}${visibleSuffix}@${domain}`;
}

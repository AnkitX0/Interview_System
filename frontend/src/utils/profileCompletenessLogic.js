/**
 * Deterministic profile completeness calculation as specified in Part 30.
 * Weights:
 * - Name: 10
 * - Target Role: 10
 * - About/Bio: 10
 * - Education: 10
 * - Skills: 15
 * - LinkedIn: 10
 * - GitHub: 10
 * - LeetCode: 10
 * - Portfolio: 5
 * - Experience Level: 10
 * Total = 100
 */
export function calculateProfileCompleteness(profile = {}, user = {}) {
  let score = 0;

  // Name: 10
  const name = user?.full_name || profile?.full_name;
  if (name && name.trim().length > 0) {
    score += 10;
  }

  // Target Role: 10
  if (profile?.target_role && profile.target_role.trim().length > 0) {
    score += 10;
  }

  // About / Bio: 10
  if (profile?.bio && profile.bio.trim().length > 0) {
    score += 10;
  }

  // Education: 10 (University or Degree)
  if (
    (profile?.university && profile.university.trim().length > 0) ||
    (profile?.degree && profile.degree.trim().length > 0)
  ) {
    score += 10;
  }

  // Skills: 15
  const sc = profile?.skills_categorized;
  let hasSkills = false;
  if (sc && typeof sc === "object") {
    if (
      (Array.isArray(sc.languages) && sc.languages.length > 0) ||
      (Array.isArray(sc.frameworks) && sc.frameworks.length > 0) ||
      (Array.isArray(sc.databases) && sc.databases.length > 0) ||
      (Array.isArray(sc.tools) && sc.tools.length > 0)
    ) {
      hasSkills = true;
    }
  } else if (Array.isArray(profile?.skills) && profile.skills.length > 0) {
    hasSkills = true;
  }
  if (hasSkills) {
    score += 15;
  }

  // Developer Profiles:
  const links = profile?.professional_links || {};

  // LinkedIn: 10
  if (links.linkedin && links.linkedin.trim().length > 0) {
    score += 10;
  }

  // GitHub: 10
  if (links.github && links.github.trim().length > 0) {
    score += 10;
  }

  // LeetCode: 10
  if (links.leetcode && links.leetcode.trim().length > 0) {
    score += 10;
  }

  // Portfolio / Website: 5
  if (
    (links.portfolio && links.portfolio.trim().length > 0) ||
    (links.website && links.website.trim().length > 0)
  ) {
    score += 5;
  }

  // Experience: 10
  if (
    (profile?.experience_level && profile.experience_level.trim().length > 0) ||
    (typeof profile?.years_experience === "number" && profile.years_experience > 0)
  ) {
    score += 10;
  }

  return Math.min(100, Math.max(0, score));
}

/**
 * Validates a profile URL format.
 */
export function isValidUrl(url) {
  if (!url || !url.trim()) return false;
  try {
    const parsed = new URL(url.trim());
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

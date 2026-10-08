import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  calculateProfileCompleteness,
  isValidUrl,
} from "./src/utils/profileCompletenessLogic.js";

describe("Profile Completeness & Validation", () => {
  it("calculates 0% for empty profile and user", () => {
    assert.equal(calculateProfileCompleteness({}, {}), 0);
  });

  it("calculates exact deterministic weighted score for populated fields", () => {
    // Name (10) + Target Role (10) + About (10) = 30
    const profile = {
      target_role: "Backend Engineer",
      bio: "Passionate about high-throughput distributed systems.",
    };
    const user = { full_name: "Ankit Singh" };
    assert.equal(calculateProfileCompleteness(profile, user), 30);
  });

  it("adds links and education to reach exact percentage", () => {
    const profile = {
      target_role: "Backend Engineer",
      bio: "Distributed systems enthusiast.",
      university: "Indian Institute of Technology",
      experience_level: "Mid-level", // 10
      skills_categorized: {
        languages: ["Python", "Go"],
        frameworks: ["FastAPI"],
      }, // 15
      professional_links: {
        github: "https://github.com/ankit", // 10
        linkedin: "https://linkedin.com/in/ankit", // 10
        leetcode: "https://leetcode.com/ankit", // 10
        portfolio: "https://ankit.dev", // 5
      },
    };
    const user = { full_name: "Ankit Singh" }; // 10
    // Total: 10 + 10 + 10 + 10 + 10 + 15 + 10 + 10 + 10 + 5 = 100%
    assert.equal(calculateProfileCompleteness(profile, user), 100);
  });

  it("validates legitimate profile URLs and rejects malformed inputs", () => {
    assert.equal(isValidUrl("https://github.com/ankit"), true);
    assert.equal(isValidUrl("http://leetcode.com/u/ankit"), true);
    assert.equal(isValidUrl("invalid-url-string"), false);
    assert.equal(isValidUrl(""), false);
    assert.equal(isValidUrl(null), false);
  });
});

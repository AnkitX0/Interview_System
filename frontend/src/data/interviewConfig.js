export const interviewTypes = {
  practice: {
    label: "Practice Mode",
    difficultyLevels: ["easy", "medium", "hard"],
    weightFocus: {
      communication: 0.5,
      behavioral: 0.5,
      technical: 0
    }
  },
  technical: {
    label: "Technical Round",
    difficultyLevels: ["easy", "medium", "hard"],
    weightFocus: {
      communication: 0.3,
      behavioral: 0.3,
      technical: 0.4
    }
  },
  hr: {
    label: "HR Round",
    difficultyLevels: ["easy", "medium"],
    weightFocus: {
      communication: 0.4,
      behavioral: 0.4,
      technical: 0.2
    }
  }
};
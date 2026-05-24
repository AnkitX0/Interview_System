export function calculateBehavioralScore({
  eyePercent,
  blinkRate,
  pauseRate
}) {
  const eyeScore = calculateEyeScore(eyePercent);
  const blinkScore = calculateBlinkScore(blinkRate);
  const pauseScore = calculatePauseScore(pauseRate);

  const finalScore =
    eyeScore * 0.4 +
    blinkScore * 0.3 +
    pauseScore * 0.3;

  return Math.round(finalScore);
}

function calculateEyeScore(percent) {
  if (percent >= 60 && percent <= 85) return 100;
  if (percent >= 40 && percent < 60)
    return 60 + (percent - 40) * 2;
  if (percent > 85 && percent <= 95)
    return 100 - (percent - 85) * 4;
  return 40;
}

function calculateBlinkScore(rate) {
  if (rate >= 15 && rate <= 20) return 100;
  if (rate > 20 && rate <= 30)
    return 100 - (rate - 20) * 3;
  if (rate < 10) return 70;
  return 50;
}

function calculatePauseScore(rate) {
  if (rate <= 2) return 100;
  if (rate <= 5) return 100 - rate * 10;
  return 40;
}
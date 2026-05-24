def calculate_behavioral_score(eye, blink, pause):

    eye_score = 100 if 60 <= eye <= 85 else max(40, eye)
    blink_score = 100 if 15 <= blink <= 20 else max(50, 100 - abs(blink - 18) * 3)
    pause_score = 100 if pause <= 2 else max(40, 100 - pause * 10)

    final = (
        eye_score * 0.4 +
        blink_score * 0.3 +
        pause_score * 0.3
    )

    return round(final, 2)
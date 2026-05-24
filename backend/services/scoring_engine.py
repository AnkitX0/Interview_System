def calculate_session_score(answer_scores, behavioral_score):

    if not answer_scores:
        return 0

    avg_answer_score = sum(answer_scores) / len(answer_scores)

    final_score = (avg_answer_score * 0.7) + (behavioral_score * 0.3)

    return final_score
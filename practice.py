import streamlit as st
import time
from database import cursor
from quiz_generators.maths import generate_maths_question
from quiz_generators.english import generate_english_question
from quiz_generators.science import generate_science_question

# =========================================================
# PRACTICE PAGE
# =========================================================
def practice_page():
    st.title("📝 Practice")

    # ---------------------------------
    # Load user grade
    # ---------------------------------
    cursor.execute("""
        SELECT grade FROM profiles WHERE user_id = ?
    """, (st.session_state.user_id,))
    
    row = cursor.fetchone()
    if not row:
        st.warning("Please complete your profile first.")
        return

    grade = int(row[0].split()[-1])

    # ---------------------------------
    # Session state
    # ---------------------------------
    if "quiz_started" not in st.session_state:
        st.session_state.quiz_started = False
    if "questions" not in st.session_state:
        st.session_state.questions = []
    if "q_index" not in st.session_state:
        st.session_state.q_index = 0
    if "score" not in st.session_state:
        st.session_state.score = 0

    # ---------------------------------
    # Quiz setup
    # ---------------------------------
    if not st.session_state.quiz_started:
        subject = st.selectbox("Choose Subject", ["Maths", "English", "Science"])

        if st.button("Start Practice", type="primary"):
            st.session_state.questions = generate_quiz(grade, subject, count=10)
            st.session_state.quiz_started = True
            st.session_state.q_index = 0
            st.session_state.score = 0
            st.rerun()
        return

    # ---------------------------------
    # Quiz finished
    # ---------------------------------
    if st.session_state.q_index >= len(st.session_state.questions):
        st.success("🎉 Practice Completed!")
        st.metric("Score", f"{st.session_state.score} / {len(st.session_state.questions)}")

        if st.button("Restart Practice"):
            for k in ["quiz_started", "questions", "q_index", "score"]:
                st.session_state.pop(k, None)
            st.rerun()
        return

    # ---------------------------------
    # Question UI
    # ---------------------------------
    question = st.session_state.questions[st.session_state.q_index]

    st.subheader(f"Question {st.session_state.q_index + 1}")
    st.write(question["q"])

    selected = st.radio(
        "Choose your answer:",
        question["options"],
        key=f"q_{st.session_state.q_index}"
    )

    # ---------------------------------
    # Timer
    # ---------------------------------
    TIME_LIMIT = 10
    start = time.time()
    timer_box = st.empty()
    progress = st.empty()

    while True:
        elapsed = int(time.time() - start)
        remaining = TIME_LIMIT - elapsed
        if remaining <= 0:
            break
        timer_box.info(f"⏳ Time left: {remaining}s")
        progress.progress(elapsed / TIME_LIMIT)
        time.sleep(0.3)

    # ---------------------------------
    # Submit
    # ---------------------------------
    if st.button("Submit Answer") or remaining <= 0:
        if selected == question["answer"]:
            st.session_state.score += 1
            st.success("✅ Correct!")
            st.balloons()
        else:
            st.error(f"❌ Wrong! Correct answer: {question['answer']}")

        time.sleep(1)
        st.session_state.q_index += 1
        st.rerun()


# =========================================================
# QUIZ GENERATOR
# =========================================================
def generate_quiz(grade, subject, count=10):
    questions = []

    for _ in range(count):
        if subject == "Maths":
            questions.append(generate_maths_question(grade))
        elif subject == "English":
            questions.append(generate_english_question(grade))
        else:
            questions.append(generate_science_question(grade))

    return questions

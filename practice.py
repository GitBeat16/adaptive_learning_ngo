import streamlit as st
import time
from database import cursor
from practice_data import PRACTICE_DATA

# =========================================================
# PRACTICE PAGE
# =========================================================
def practice_page():
    st.title("📝 Practice Quiz")

    # -------------------------------------------------
    # Load user grade from DB
    # -------------------------------------------------
    cursor.execute("""
        SELECT grade
        FROM profiles
        WHERE user_id = ?
    """, (st.session_state.user_id,))
    
    row = cursor.fetchone()
    if not row:
        st.warning("Please complete your profile first.")
        return

    grade = int(row[0].split()[-1])

    if grade not in PRACTICE_DATA:
        st.info("Practice content coming soon for your grade.")
        return

    data = PRACTICE_DATA[grade]

    # -------------------------------------------------
    # SESSION STATE INIT
    # -------------------------------------------------
    if "quiz_started" not in st.session_state:
        st.session_state.quiz_started = False
    if "q_index" not in st.session_state:
        st.session_state.q_index = 0
    if "score" not in st.session_state:
        st.session_state.score = 0
    if "feedback" not in st.session_state:
        st.session_state.feedback = None

    # -------------------------------------------------
    # QUIZ SETUP
    # -------------------------------------------------
    if not st.session_state.quiz_started:
        subject = st.selectbox("Select Subject", list(data.keys()))
        topic = st.selectbox("Select Topic", list(data[subject].keys()))

        if st.button("Start Quiz", type="primary"):
            st.session_state.subject = subject
            st.session_state.topic = topic
            st.session_state.questions = data[subject][topic]
            st.session_state.quiz_started = True
            st.session_state.q_index = 0
            st.session_state.score = 0
            st.rerun()
        return

    # -------------------------------------------------
    # QUIZ IN PROGRESS
    # -------------------------------------------------
    questions = st.session_state.questions
    q_index = st.session_state.q_index

    if q_index >= len(questions):
        st.success("🎉 Quiz Completed!")
        st.metric("Final Score", f"{st.session_state.score} / {len(questions)}")

        if st.button("Restart Quiz"):
            for k in ["quiz_started", "q_index", "score", "feedback"]:
                st.session_state.pop(k, None)
            st.rerun()
        return

    question = questions[q_index]

    # -------------------------------------------------
    # TIMER (PER QUESTION)
    # -------------------------------------------------
    timer_placeholder = st.empty()
    progress_placeholder = st.empty()

    TIME_LIMIT = 10  # seconds
    start_time = time.time()

    # -------------------------------------------------
    # QUESTION UI
    # -------------------------------------------------
    st.subheader(f"Question {q_index + 1} of {len(questions)}")
    st.write(question["q"])

    answer = st.radio(
        "Choose your answer:",
        question["options"],
        key=f"q_{q_index}"
    )

    # -------------------------------------------------
    # LIVE TIMER ANIMATION
    # -------------------------------------------------
    elapsed = 0
    while elapsed < TIME_LIMIT:
        elapsed = int(time.time() - start_time)
        remaining = TIME_LIMIT - elapsed
        timer_placeholder.info(f"⏳ Time left: {remaining}s")
        progress_placeholder.progress(elapsed / TIME_LIMIT)
        time.sleep(0.3)

        if st.session_state.feedback is not None:
            break

    # -------------------------------------------------
    # SUBMIT / AUTO-SUBMIT
    # -------------------------------------------------
    if st.button("Submit Answer") or elapsed >= TIME_LIMIT:

        if answer == question["answer"]:
            st.session_state.score += 1
            st.session_state.feedback = "correct"
            st.success("✅ Correct!")
            st.balloons()
        else:
            st.session_state.feedback = "wrong"
            st.error(f"❌ Wrong! Correct answer: {question['answer']}")

        time.sleep(1)

        st.session_state.q_index += 1
        st.session_state.feedback = None
        st.rerun()

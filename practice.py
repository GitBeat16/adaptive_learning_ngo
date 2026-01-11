import streamlit as st
import time
from database import cursor
from quiz_generators.maths import generate_maths_question
from quiz_generators.english import generate_english_question
from quiz_generators.science import generate_science_question


def practice_page():
    st.title("📝 Practice")

    # -----------------------------
    # Load grade
    # -----------------------------
    cursor.execute("SELECT grade FROM profiles WHERE user_id = ?", (st.session_state.user_id,))
    row = cursor.fetchone()
    if not row:
        st.warning("Please complete your profile first.")
        return

    grade = int(row[0].split()[-1])

    # -----------------------------
    # Session state init
    # -----------------------------
    if "quiz_started" not in st.session_state:
        st.session_state.quiz_started = False
    if "questions" not in st.session_state:
        st.session_state.questions = []
    if "q_index" not in st.session_state:
        st.session_state.q_index = 0
    if "score" not in st.session_state:
        st.session_state.score = 0
    if "start_time" not in st.session_state:
        st.session_state.start_time = None

    # -----------------------------
    # Start quiz
    # -----------------------------
    if not st.session_state.quiz_started:
        subject = st.selectbox("Choose Subject", ["Maths", "English", "Science"])

        if st.button("Start Practice", type="primary"):
            st.session_state.questions = generate_quiz(grade, subject, count=10)
            st.session_state.quiz_started = True
            st.session_state.q_index = 0
            st.session_state.score = 0
            st.session_state.start_time = time.time()
            st.rerun()
        return

    # -----------------------------
    # Quiz finished
    # -----------------------------
    if st.session_state.q_index >= len(st.session_state.questions):
        st.success("🎉 Practice Completed!")
        st.metric("Score", f"{st.session_state.score} / {len(st.session_state.questions)}")

        if st.button("Restart Practice"):
            for k in ["quiz_started", "questions", "q_index", "score", "start_time"]:
                st.session_state.pop(k, None)
            st.rerun()
        return

    # -----------------------------
    # Current question
    # -----------------------------
    question = st.session_state.questions[st.session_state.q_index]

    st.subheader(f"Question {st.session_state.q_index + 1} of {len(st.session_state.questions)}")
    st.write(question["q"])

    selected = st.radio(
        "Choose your answer:",
        question["options"],
        key=f"q_{st.session_state.q_index}"
    )

    # -----------------------------
    # Timer (NON-BLOCKING)
    # -----------------------------
    TIME_LIMIT = 10
    elapsed = int(time.time() - st.session_state.start_time)
    remaining = max(0, TIME_LIMIT - elapsed)

    st.info(f"⏳ Time left: {remaining}s")
    st.progress((TIME_LIMIT - remaining) / TIME_LIMIT)

    # -----------------------------
    # Auto-submit on timeout
    # -----------------------------
    if remaining == 0:
        submit_answer(selected, question)
        return

    # -----------------------------
    # Submit button
    # -----------------------------
    if st.button("Submit Answer"):
        submit_answer(selected, question)


def submit_answer(selected, question):
    if selected == question["answer"]:
        st.session_state.score += 1
        st.success("✅ Correct!")
        st.balloons()
    else:
        st.error(f"❌ Wrong! Correct answer: {question['answer']}")

    time.sleep(0.8)
    st.session_state.q_index += 1
    st.session_state.start_time = time.time()
    st.rerun()


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

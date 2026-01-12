import streamlit as st
from practice_data import PRACTICE_DATA
from database import cursor
from streak import init_streak, update_streak

def practice_page():

    # ✅ REQUIRED: initialize streak system
    init_streak()

    if not st.session_state.get("user_id"):
        st.warning("Please log in to access practice.")
        return

    cursor.execute("""
        SELECT role, class_level
        FROM profiles
        WHERE user_id = ?
    """, (st.session_state.user_id,))
    profile = cursor.fetchone()

    if not profile:
        st.warning("Please complete your profile first.")
        return

    role, class_level = profile

    st.subheader("Practice Questions")

    if role == "Student":
        st.info(f"Class: {class_level}")
    else:
        class_level = st.selectbox(
            "Select Class",
            sorted(PRACTICE_DATA.keys())
        )

    if class_level not in PRACTICE_DATA:
        st.warning("Practice not available for this class yet.")
        return

    subject = st.selectbox(
        "Select Subject",
        list(PRACTICE_DATA[class_level].keys())
    )

    topic = st.selectbox(
        "Select Topic",
        list(PRACTICE_DATA[class_level][subject].keys())
    )

    questions = PRACTICE_DATA[class_level][subject][topic]

    st.divider()
    st.markdown("### Answer the following questions")

    user_answers = []

    for i, q in enumerate(questions):
        ans = st.radio(
            f"Q{i + 1}. {q['q']}",
            q["options"],
            key=f"practice_q_{i}"
        )
        user_answers.append(ans)

    if st.button("Submit Practice"):
        score = sum(
            1 for i, q in enumerate(questions)
            if user_answers[i] == q["answer"]
        )

        st.success(f"Your Score: {score} / {len(questions)}")

        # ✅ streak update now SAFE
        update_streak()

        if score == len(questions):
            st.balloons()

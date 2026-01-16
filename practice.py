import streamlit as st
import re
from practice_data import PRACTICE_DATA
from database import cursor
from streak import init_streak, update_streak

def get_normalized_class_level(user_id):
    """
    Helper to extract the integer class level from the database.
    Checks both 'class_level' (int) and 'grade' (string like 'Grade 5').
    """
    cursor.execute("""
        SELECT class_level, grade 
        FROM profiles 
        WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    
    if not row:
        return None
        
    class_level_raw, grade_str = row
    
    # 1. Try the integer column first
    if class_level_raw is not None and str(class_level_raw).isdigit():
        return int(class_level_raw)
        
    # 2. If that's empty, extract the number from the 'grade' string (e.g., "Grade 5" -> 5)
    if grade_str:
        nums = re.findall(r'\d+', str(grade_str))
        if nums:
            return int(nums[0])
            
    return None

def practice_page():
    # ✅ REQUIRED: initialize streak system
    init_streak()

    if not st.session_state.get("user_id"):
        st.warning("Please log in to access practice.")
        return

    # Fetch normalized class level
    class_level = get_normalized_class_level(st.session_state.user_id)
    
    # Fetch role for UI logic
    cursor.execute("SELECT role FROM profiles WHERE user_id = ?", (st.session_state.user_id,))
    role_row = cursor.fetchone()
    role = role_row[0] if role_row else "Student"

    if class_level is None and role == "Student":
        st.warning("Please complete your profile in the Dashboard to set your Grade.")
        if st.button("Go to Dashboard"):
            st.session_state.page = "Dashboard"
            st.rerun()
        return

    st.title("📝 Practice Zone")
    st.caption("Sharpen your knowledge with curriculum-based exercises.")

    # ---------------------------------------------------------
    # CLASS SELECTION
    # ---------------------------------------------------------
    if role == "Student":
        st.info(f"✨ Showing materials for **Grade {class_level}**")
    else:
        # Teachers/Admins can select any class
        available_classes = sorted(PRACTICE_DATA.keys())
        class_level = st.selectbox(
            "Select Class to Preview",
            available_classes,
            index=available_classes.index(class_level) if class_level in available_classes else 0
        )

    # Check if data exists for this specific level
    if class_level not in PRACTICE_DATA:
        st.error(f"⚠️ Class {class_level} data not found.")
        st.info("Our team is currently uploading questions for this level. Please try another grade.")
        return

    # ---------------------------------------------------------
    # SUBJECT & TOPIC SELECTION
    # ---------------------------------------------------------
    col1, col2 = st.columns(2)
    
    with col1:
        subject = st.selectbox(
            "Select Subject",
            list(PRACTICE_DATA[class_level].keys())
        )

    with col2:
        topic = st.selectbox(
            "Select Topic",
            list(PRACTICE_DATA[class_level][subject].keys())
        )

    questions = PRACTICE_DATA[class_level][subject][topic]

    st.divider()
    st.markdown(f"### Quiz: {topic}")
    st.write(f"Answer the {len(questions)} questions below to maintain your streak!")

    user_answers = []

    # ---------------------------------------------------------
    # QUESTION RENDERING
    # ---------------------------------------------------------
    for i, q in enumerate(questions):
        st.markdown(f"**Q{i + 1}. {q['q']}**")
        ans = st.radio(
            "Choose one:",
            q["options"],
            key=f"practice_q_{class_level}_{i}",
            label_visibility="collapsed"
        )
        user_answers.append(ans)
        st.write("") # Padding

    if st.button("Submit Practice", use_container_width=True):
        score = sum(
            1 for i, q in enumerate(questions)
            if user_answers[i] == q["answer"]
        )

        if score == len(questions):
            st.balloons()
            st.success(f"Perfect Score! {score}/{len(questions)} 🎯")
        elif score >= len(questions) // 2:
            st.success(f"Good job! Your Score: {score}/{len(questions)} 👍")
        else:
            st.warning(f"Keep practicing! Your Score: {score}/{len(questions)}")

        # ✅ Update streak on submission
        update_streak()
        st.info("🔥 Your streak has been updated!")

import streamlit as st
from database import cursor

def practice_page():
    st.title("Practice")

    # ---------------------------------
    # Load profile from database
    # ---------------------------------
    cursor.execute("""
        SELECT role, grade, strong_subjects, weak_subjects, teaches
        FROM profiles
        WHERE user_id = ?
    """, (st.session_state.user_id,))

    profile = cursor.fetchone()

    if not profile:
        st.warning("Please complete your profile in Matchmaking first.")
        return

    role, grade, strong, weak, teaches = profile

    # ---------------------------------
    # Practice logic
    # ---------------------------------
    st.subheader("Your Practice Area")
    st.write("**Role:**", role)
    st.write("**Grade:**", grade)

    if role == "Student":
        subjects = (weak or strong or "").split(",")
        st.write("Focus Subjects:")
    else:
        subjects = (teaches or "").split(",")
        st.write("Subjects You Teach:")

    subjects = [s for s in subjects if s]

    if not subjects:
        st.info("No subjects found. Update your profile.")
        return

    subject = st.selectbox("Choose Subject", subjects)

    st.success(f"Practice content for **{subject}** coming soon 🚀")

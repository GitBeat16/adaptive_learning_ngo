import streamlit as st
import time
from datetime import timedelta
from database import cursor, conn
from streak import init_streak, render_streak_ui

# -----------------------------------------------------
# CONSTANTS
# -----------------------------------------------------
SUBJECTS = ["Mathematics", "English", "Science"]
TIME_SLOTS = ["4-5 PM", "5-6 PM", "6-7 PM"]

# -----------------------------------------------------
# HELPERS
# -----------------------------------------------------
def calculate_streak(dates):
    if not dates:
        return 0

    dates = sorted(set(dates), reverse=True)
    streak = 1
    for i in range(len(dates) - 1):
        if dates[i] - dates[i + 1] == timedelta(days=1):
            streak += 1
        else:
            break
    return streak


# =====================================================
# DASHBOARD PAGE
# =====================================================
def dashboard_page():

    # ✅ INIT STREAK SYSTEM (REQUIRED)
    init_streak()

    # -------------------------------------------------
    # HERO
    # -------------------------------------------------
    st.title(f"Welcome back, {st.session_state.user_name}")
    st.caption("Your learning journey at a glance")
    st.divider()

    # -------------------------------------------------
    # PROFILE FETCH
    # -------------------------------------------------
    cursor.execute("""
        SELECT role, grade, time, strong_subjects, weak_subjects, teaches
        FROM profiles
        WHERE user_id = ?
    """, (st.session_state.user_id,))
    profile = cursor.fetchone()

    edit_mode = st.session_state.get("edit_profile", False)

    # -------------------------------------------------
    # PROFILE SETUP / EDIT
    # -------------------------------------------------
    if not profile or edit_mode:
        st.subheader("Profile Setup")

        with st.form("profile_form"):
            role = st.radio("Role", ["Student", "Teacher"], horizontal=True)
            grade = st.selectbox("Grade", [f"Grade {i}" for i in range(1, 11)])
            class_level = int(grade.split()[-1])
            time_slot = st.selectbox("Available Time Slot", TIME_SLOTS)

            strong, weak, teaches = [], [], []

            if role == "Student":
                strong = st.multiselect("Strong Subjects", SUBJECTS)
                weak = st.multiselect("Weak Subjects", SUBJECTS)
            else:
                teaches = st.multiselect("Subjects You Teach", SUBJECTS)

            submitted = st.form_submit_button("Save Profile")

        if submitted:
            cursor.execute("""
                INSERT OR REPLACE INTO profiles (
                    user_id,
                    role,
                    grade,
                    class_level,
                    time,
                    strong_subjects,
                    weak_subjects,
                    teaches,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'waiting')
            """, (
                st.session_state.user_id,
                role,
                grade,
                class_level,
                time_slot,
                ",".join(strong),
                ",".join(weak),
                ",".join(teaches)
            ))
            conn.commit()

            st.session_state.edit_profile = False
            st.success("Profile saved successfully.")
            st.rerun()

        return

    # -------------------------------------------------
    # PROFILE VIEW
    # -------------------------------------------------
    role, grade, time_slot, strong, weak, teaches = profile

    strong_list = strong.split(",") if strong else []
    weak_list = weak.split(",") if weak else []
    teach_list = teaches.split(",") if teaches else []

    st.subheader("Profile Overview")

    p1, p2, p3 = st.columns(3)
    p1.metric("Role", role)
    p2.metric("Grade", grade)
    p3.metric("Time Slot", time_slot)

    st.divider()

    # -------------------------------------------------
    # STREAK UI (NEW — SAVED & SHOWN)
    # -------------------------------------------------
    render_streak_ui()

    st.divider()

    # -------------------------------------------------
    # SUBJECTS
    # -------------------------------------------------
    s1, s2 = st.columns(2)

    with s1:
        st.markdown("### Strong Subjects")
        if strong_list or teach_list:
            for subject in (strong_list or teach_list):
                st.success(subject)
        else:
            st.info("No strong subjects added")

    with s2:
        st.markdown("### Weak Subjects")
        if weak_list:
            for subject in weak_list:
                st.error(subject)
        else:
            st.info("No weak subjects added")

    st.divider()

    if st.button("Edit Profile"):
        st.session_state.edit_profile = True
        st.rerun()

    # -------------------------------------------------
    # SESSION DATA
    # -------------------------------------------------
    cursor.execute("""
        SELECT mentor, rating, session_date
        FROM ratings
        WHERE mentor = ? OR mentee = ?
    """, (st.session_state.user_name, st.session_state.user_name))

    rows = cursor.fetchall()
    session_dates = [r[2] for r in rows]

    streak = calculate_streak(session_dates)
    total_sessions = len(rows)
    avg_rating = round(sum(r[1] for r in rows) / total_sessions, 2) if total_sessions else "—"

    # -------------------------------------------------
    # STATS
    # -------------------------------------------------
    st.subheader("Progress")

    c1, c2, c3, c4 = st.columns(4)
    time.sleep(0.15)

    c1.metric("Learning Streak (days)", streak)
    c2.metric("Sessions Completed", total_sessions)
    c3.metric("Average Rating", avg_rating)
    c4.metric("Consistency", f"{min(streak / 30 * 100, 100):.0f}%")

    st.progress(min(streak / 30, 1.0))

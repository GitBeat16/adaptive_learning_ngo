import streamlit as st
import time
from datetime import timedelta
from database import cursor, conn

SUBJECTS = ["Mathematics", "English", "Science"]
TIME_SLOTS = ["4-5 PM", "5-6 PM", "6-7 PM"]

# =========================================================
# HELPERS
# =========================================================
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


# =========================================================
# DASHBOARD PAGE
# =========================================================
def dashboard_page():

    # -----------------------------------------------------
    # STYLES (AVATAR + CHIPS + CARD)
    # -----------------------------------------------------
    st.markdown("""
    <style>
    .profile-card {
        display: flex;
        gap: 1.5rem;
        align-items: flex-start;
    }

    .avatar {
        width: 72px;
        height: 72px;
        border-radius: 50%;
        background: linear-gradient(135deg,#6366f1,#4f46e5);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        flex-shrink: 0;
    }

    .avatar svg {
        width: 36px;
        height: 36px;
        fill: white;
    }

    .profile-details p {
        margin: 0.25rem 0;
    }

    .subject-section {
        margin-top: 0.75rem;
    }

    .subject-chip {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 500;
        margin-right: 6px;
        margin-top: 6px;
    }

    .chip-strong {
        background: rgba(34,197,94,0.15);
        color: #15803d;
    }

    .chip-weak {
        background: rgba(239,68,68,0.15);
        color: #b91c1c;
    }

    @media (prefers-color-scheme: dark) {
        .chip-strong {
            background: rgba(34,197,94,0.25);
            color: #4ade80;
        }
        .chip-weak {
            background: rgba(239,68,68,0.25);
            color: #f87171;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    # -----------------------------------------------------
    # HERO
    # -----------------------------------------------------
    st.markdown(f"""
    <div class="card" style="background:linear-gradient(135deg,#6366f1,#4f46e5);color:white;">
        <h2>Welcome back, {st.session_state.user_name}</h2>
        <p>Your learning journey at a glance.</p>
    </div>
    """, unsafe_allow_html=True)

    # -----------------------------------------------------
    # PROFILE FETCH
    # -----------------------------------------------------
    cursor.execute("""
        SELECT role, grade, time, strong_subjects, weak_subjects, teaches
        FROM profiles
        WHERE user_id = ?
    """, (st.session_state.user_id,))
    profile = cursor.fetchone()

    edit_mode = st.session_state.get("edit_profile", False)

    # =====================================================
    # PROFILE SETUP / EDIT
    # =====================================================
    if not profile or edit_mode:
        st.subheader("Profile Setup")

        with st.form("profile_form"):
            role = st.radio("Role", ["Student", "Teacher"], horizontal=True)
            grade = st.selectbox("Grade", [f"Grade {i}" for i in range(1, 11)])
            time_slot = st.selectbox("Available Time Slot", TIME_SLOTS)

            strong, weak, teaches = [], [], []

            if role == "Student":
                strong = st.multiselect("Strong Subjects", SUBJECTS)
                weak = st.multiselect("Weak Subjects", SUBJECTS)
            else:
                teaches = st.multiselect("Subjects You Teach", SUBJECTS)

            submitted = st.form_submit_button("Save Profile")

        if submitted:
            cursor.execute("DELETE FROM profiles WHERE user_id = ?", (st.session_state.user_id,))
            cursor.execute("""
                INSERT INTO profiles
                (user_id, role, grade, class, time, strong_subjects, weak_subjects, teaches)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                st.session_state.user_id,
                role,
                grade,
                int(grade.split()[-1]),
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

    # =====================================================
    # PROFILE VIEW
    # =====================================================
    role, grade, time_slot, strong, weak, teaches = profile
    strong_list = strong.split(",") if strong else []
    weak_list = weak.split(",") if weak else []
    teach_list = teaches.split(",") if teaches else []

    strong_chips = "".join(
        f"<span class='subject-chip chip-strong'>{s}</span>"
        for s in (strong_list or teach_list)
    ) or "<span>—</span>"

    weak_chips = "".join(
        f"<span class='subject-chip chip-weak'>{w}</span>"
        for w in weak_list
    ) or "<span>—</span>"

    # -----------------------------------------------------
    # PROFILE CARD (FIXED RENDERING)
    # -----------------------------------------------------
    st.markdown(f"""
    <div class="card">
        <div class="profile-card">
            <div class="avatar">
                <svg viewBox="0 0 24 24">
                    <circle cx="12" cy="8" r="4"/>
                    <path d="M4 20c0-4 4-6 8-6s8 2 8 6"/>
                </svg>
            </div>

            <div class="profile-details">
                <h3>Your Profile</h3>
                <p><strong>Role:</strong> {role}</p>
                <p><strong>Grade:</strong> {grade}</p>
                <p><strong>Time Slot:</strong> {time_slot}</p>

                <div class="subject-section">
                    <strong>Strong Subjects</strong><br>
                    {strong_chips}
                </div>

                <div class="subject-section">
                    <strong>Weak Subjects</strong><br>
                    {weak_chips}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Edit Profile"):
        st.session_state.edit_profile = True
        st.rerun()

    # -----------------------------------------------------
    # SESSION DATA
    # -----------------------------------------------------
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

    # -----------------------------------------------------
    # STATS
    # -----------------------------------------------------
    st.subheader("Your Progress")

    c1, c2, c3, c4 = st.columns(4)
    time.sleep(0.2)

    c1.metric("Day Streak", streak)
    c2.metric("Sessions", total_sessions)
    c3.metric("Avg Rating", avg_rating)
    c4.metric("Consistency", f"{min(streak/30*100,100):.0f}%")

    st.progress(min(streak / 30, 1.0))

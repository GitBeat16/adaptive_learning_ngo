import streamlit as st
import time
from datetime import date, timedelta
from database import cursor

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
    # HERO
    # -----------------------------------------------------
    st.markdown(f"""
    <div class="card" style="
        background: linear-gradient(135deg, #6366f1, #4f46e5);
        color: white;
    ">
        <h2>Welcome back, {st.session_state.user_name}</h2>
        <p>Track your learning, mentoring, and impact — all in one place.</p>
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

    if not profile:
        st.warning("Please complete your profile to unlock your dashboard.")
        return

    role, grade, time_slot, strong, weak, teaches = profile
    subjects = (teaches or strong or weak or "—").replace(",", ", ")

    # -----------------------------------------------------
    # PROFILE CARD
    # -----------------------------------------------------
    st.markdown(f"""
    <div class="card">
        <h3>Your Profile</h3>
        <div style="display:flex; gap:2rem; flex-wrap:wrap;">
            <div><strong>Role</strong><br>{role}</div>
            <div><strong>Grade</strong><br>{grade}</div>
            <div><strong>Time Slot</strong><br>{time_slot}</div>
            <div><strong>Subjects</strong><br>{subjects}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

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
    # LEADERBOARD
    # -----------------------------------------------------
    cursor.execute("""
        SELECT mentor, COUNT(*) AS sessions, AVG(rating) AS avg_rating
        FROM ratings
        GROUP BY mentor
        ORDER BY sessions DESC, avg_rating DESC
    """)
    leaderboard = cursor.fetchall()

    leaderboard_rank = next(
        (i + 1 for i, r in enumerate(leaderboard) if r[0] == st.session_state.user_name),
        "—"
    )

    # -----------------------------------------------------
    # STATS SECTION
    # -----------------------------------------------------
    st.markdown("### Your Progress")

    c1, c2, c3, c4 = st.columns(4)

    with st.spinner("Loading insights..."):
        time.sleep(0.4)

    with c1:
        st.markdown(f"""
        <div class="card" style="background:#ecfeff;">
            <h2>{streak}</h2>
            <p>Day Streak</p>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="card" style="background:#f0fdf4;">
            <h2>#{leaderboard_rank}</h2>
            <p>Leaderboard Rank</p>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="card" style="background:#fff7ed;">
            <h2>{total_sessions}</h2>
            <p>Sessions Completed</p>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="card" style="background:#fdf4ff;">
            <h2>{avg_rating}</h2>
            <p>Average Rating</p>
        </div>
        """, unsafe_allow_html=True)

    # -----------------------------------------------------
    # PROGRESS BAR
    # -----------------------------------------------------
    st.markdown("**Consistency Goal (30 days)**")
    st.progress(min(streak / 30, 1.0))

    st.divider()

    # -----------------------------------------------------
    # SESSION HISTORY
    # -----------------------------------------------------
    st.markdown("### Recent Sessions")

    if rows:
        history = []
        for r in rows[-10:][::-1]:
            history.append({
                "Partner": r[0],
                "Rating": r[1],
                "Date": r[2].strftime("%d %b %Y")
            })
        st.dataframe(history, use_container_width=True)
    else:
        st.info("No sessions yet — start matchmaking to begin your journey.")

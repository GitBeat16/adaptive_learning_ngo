import streamlit as st
from database import cursor

def admin_page():
    st.title("Admin Dashboard")
    st.caption("Overview of users, roles, activity, and session feedback")
    st.divider()

    # =================================================
    # PLATFORM STATISTICS
    # =================================================
    st.subheader("Platform Statistics")

    cursor.execute("SELECT COUNT(*) FROM auth_users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM profiles WHERE role='Student'")
    students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM profiles WHERE role='Teacher'")
    teachers = cursor.fetchone()[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Signups", total_users)
    c2.metric("Students", students)
    c3.metric("Teachers", teachers)

    st.divider()

    # =================================================
    # REGISTERED USERS
    # =================================================
    st.subheader("Registered Users")

    cursor.execute("""
        SELECT 
            a.id,
            a.name,
            a.email,
            p.role,
            p.grade,
            p.class_level,
            p.time,
            p.strong_subjects,
            p.weak_subjects,
            p.teaches
        FROM auth_users a
        LEFT JOIN profiles p ON a.id = p.user_id
        ORDER BY a.id DESC
    """)

    users = cursor.fetchall()

    if not users:
        st.info("No users registered yet.")
        return

    for u in users:
        (
            user_id,
            name,
            email,
            role,
            grade,
            class_level,
            time_slot,
            strong,
            weak,
            teaches
        ) = u

        with st.expander(f"{name}  |  {email}"):
            st.write(f"**User ID:** {user_id}")
            st.write(f"**Role:** {role or 'Not set'}")
            st.write(f"**Grade:** {grade or '—'}")
            st.write(f"**Class Level:** {class_level or '—'}")
            st.write(f"**Time Slot:** {time_slot or '—'}")
            st.write(f"**Strong Subjects:** {strong or '—'}")
            st.write(f"**Weak Subjects:** {weak or '—'}")
            st.write(f"**Teaches:** {teaches or '—'}")

    st.divider()

    # =================================================
    # SESSION RATINGS (NEW – AUDIT VIEW)
    # =================================================
    st.subheader("Session Ratings (All Sessions)")

    cursor.execute("""
        SELECT 
            match_id,
            rater_name,
            rating,
            rated_at
        FROM session_ratings
        ORDER BY rated_at DESC
    """)

    session_ratings = cursor.fetchall()

    if not session_ratings:
        st.info("No session ratings submitted yet.")
    else:
        for mid, name, rating, date in session_ratings:
            st.markdown(f"""
            <div class="card">
                <b>Session:</b> {mid}<br>
                <b>Rated By:</b> {name}<br>
                <b>Rating:</b> ⭐ {rating}<br>
                <b>Date:</b> {date}
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # =================================================
    # TOP RATED USERS (SESSION-BASED)
    # =================================================
    st.subheader("Top Rated Users (Based on Sessions)")

    cursor.execute("""
        SELECT 
            rater_name,
            AVG(rating) AS avg_rating,
            COUNT(*) AS total_sessions
        FROM session_ratings
        GROUP BY rater_name
        HAVING total_sessions >= 1
        ORDER BY avg_rating DESC, total_sessions DESC
    """)

    leaderboard = cursor.fetchall()

    if not leaderboard:
        st.info("No leaderboard data yet.")
    else:
        for i, row in enumerate(leaderboard, 1):
            name, avg, count = row
            st.write(
                f"{i}. **{name}** — ⭐ {round(avg, 2)} "
                f"({count} sessions)"
            )

    st.divider()

    # =================================================
    # LEGACY MENTOR LEADERBOARD (KEPT)
    # =================================================
    st.subheader("Legacy Mentor Leaderboard")

    cursor.execute("""
        SELECT mentor, AVG(rating) AS avg_rating, COUNT(*) AS total_sessions
        FROM ratings
        GROUP BY mentor
        ORDER BY avg_rating DESC
    """)

    legacy = cursor.fetchall()

    if not legacy:
        st.info("No legacy ratings yet.")
    else:
        for i, r in enumerate(legacy, 1):
            st.write(
                f"{i}. **{r[0]}** — ⭐ {round(r[1], 2)} "
                f"({r[2]} sessions)"
            )

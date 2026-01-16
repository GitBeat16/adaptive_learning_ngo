import streamlit as st
from database import cursor

def admin_page():
    st.title("🛡️ Admin Control Center")
    st.caption("Comprehensive overview of users, network health, and session quality.")
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

    cursor.execute("SELECT COUNT(*) FROM session_ratings")
    total_sessions = cursor.fetchone()[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Signups", total_users)
    c2.metric("Students", students)
    c3.metric("Teachers", teachers)
    c4.metric("Sessions Rated", total_sessions)

    st.divider()

    # =================================================
    # REGISTERED USERS & THEIR FEEDBACK
    # =================================================
    st.subheader("User Directory & Performance")

    cursor.execute("""
        SELECT 
            a.id, a.name, a.email, 
            p.role, p.grade, p.time,
            p.strong_subjects, p.weak_subjects, p.teaches,
            (SELECT AVG(rating) FROM session_ratings sr 
             JOIN profiles pr ON pr.match_id = sr.match_id 
             WHERE pr.user_id = a.id AND sr.rater_id != a.id) as avg_rating
        FROM auth_users a
        LEFT JOIN profiles p ON a.id = p.user_id
        ORDER BY a.id DESC
    """)
    users = cursor.fetchall()

    if not users:
        st.info("No users registered yet.")
    else:
        for u in users:
            uid, name, email, role, grade, time_slot, strong, weak, teaches, avg_r = u
            rating_display = f"⭐ {round(avg_r, 2)}" if avg_r else "No ratings"
            
            with st.expander(f"👤 {name} ({role or 'No Role'}) — {rating_display}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Email:** {email}")
                    st.write(f"**Grade:** {grade or '—'}")
                    st.write(f"**Availability:** {time_slot or '—'}")
                with col2:
                    if role == "Student":
                        st.write(f"**Strong:** {strong or '—'}")
                        st.write(f"**Weak:** {weak or '—'}")
                    else:
                        st.write(f"**Teaches:** {teaches or '—'}")
                
                # Show specific feedback for THIS user
                st.markdown("---")
                st.markdown("**Recent Feedback for this User:**")
                cursor.execute("""
                    SELECT sr.rating, sr.feedback, sr.rated_at, au.name 
                    FROM session_ratings sr
                    JOIN auth_users au ON sr.rater_id = au.id
                    JOIN profiles p ON sr.match_id = p.match_id
                    WHERE p.user_id = ? AND sr.rater_id != ?
                    ORDER BY sr.rated_at DESC LIMIT 3
                """, (uid, uid))
                feedbacks = cursor.fetchall()
                if feedbacks:
                    for r, f, d, rater in feedbacks:
                        st.caption(f"📅 {d} | Rated {r}/5 by {rater}")
                        st.info(f if f else "No text feedback provided.")
                else:
                    st.write("No session feedback yet.")

    st.divider()

    # =================================================
    # ALL SESSION AUDIT
    # =================================================
    st.subheader("Global Session Audit")

    cursor.execute("""
        SELECT 
            sr.match_id, 
            au.name as rater, 
            sr.rating, 
            sr.feedback, 
            sr.rated_at
        FROM session_ratings sr
        JOIN auth_users au ON sr.rater_id = au.id
        ORDER BY sr.rated_at DESC
    """)
    session_logs = cursor.fetchall()

    if not session_logs:
        st.info("No session ratings submitted yet.")
    else:
        # Display as a table for cleaner admin viewing
        audit_data = []
        for mid, rater, rat, feed, date in session_logs:
            audit_data.append({
                "Session ID": mid,
                "Rater": rater,
                "Rating": f"{rat}/5",
                "Feedback": feed,
                "Date": date
            })
        st.table(audit_data)

    st.divider()

    # =================================================
    # TOP PERFORMERS (LEADERBOARD)
    # =================================================
    st.subheader("Top Rated Learning Partners")

    # This query finds users based on ratings received from others
    cursor.execute("""
        SELECT 
            a.name, 
            AVG(sr.rating) as score, 
            COUNT(sr.id) as sessions
        FROM auth_users a
        JOIN profiles p ON a.id = p.user_id
        JOIN session_ratings sr ON p.match_id = sr.match_id
        WHERE sr.rater_id != a.id
        GROUP BY a.id
        ORDER BY score DESC
    """)
    leaderboard = cursor.fetchall()

    if not leaderboard:
        st.info("Leaderboard will populate after sessions are rated.")
    else:
        for i, row in enumerate(leaderboard[:10], 1):
            lname, lscore, lcount = row
            st.write(f"{i}. **{lname}** — ⭐ {round(lscore, 2)} ({lcount} reviews)")

    if st.button("Refresh Admin Data"):
        st.rerun()

import streamlit as st
from database import cursor

def admin_page():
    st.title("Admin Dashboard")

    st.divider()

    # =========================
    # USERS OVERVIEW
    # =========================
    st.subheader("Registered Users")

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    if not users:
        st.info("No users registered yet.")
        return

    for u in users:
        with st.expander(f"{u[0]} ({u[1]})"):
            st.write(f"Grade: {u[2]}")
            st.write(f"Class: {u[3]}")
            st.write(f"Time Slot: {u[4]}")
            st.write(f"Strong Subjects: {u[5]}")
            st.write(f"Weak Subjects: {u[6]}")
            st.write(f"Teaches: {u[7]}")

    st.divider()

    # =========================
    # USER COUNTS
    # =========================
    st.subheader("User Statistics")

    cursor.execute("SELECT COUNT(*) FROM users WHERE role='Student'")
    students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role='Teacher'")
    teachers = cursor.fetchone()[0]

    col1, col2 = st.columns(2)
    col1.metric("Students", students)
    col2.metric("Teachers", teachers)

    st.divider()

    # =========================
    # RATINGS & LEADERBOARD
    # =========================
    st.subheader("Mentor Leaderboard")

    cursor.execute("""
        SELECT mentor, AVG(rating) as avg_rating, COUNT(*) as total
        FROM ratings
        GROUP BY mentor
        ORDER BY avg_rating DESC
    """)

    ratings = cursor.fetchall()

    if not ratings:
        st.info("No ratings yet.")
    else:
        for i, r in enumerate(ratings, 1):
            st.write(
                f"{i}. {r[0]} — ⭐ {round(r[1],2)} "
                f"({r[2]} sessions)"
            )

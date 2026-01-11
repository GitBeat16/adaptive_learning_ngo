import streamlit as st
from matching import get_peer_matches
from ratings import submit_rating
from practice_data import get_practice_data
from streak import get_streak

# -------------------------------------------------
# Page Config
# -------------------------------------------------
st.set_page_config(
    page_title="Adaptive Learning NGO",
    layout="wide"
)

# -------------------------------------------------
# Session State Initialization
# -------------------------------------------------
if "user_id" not in st.session_state:
    st.session_state.user_id = "demo_user"

if "role" not in st.session_state:
    st.session_state.role = "Student"

# -------------------------------------------------
# Sidebar Navigation
# -------------------------------------------------
st.sidebar.title("📚 Adaptive Learning NGO")

page = st.sidebar.radio(
    "Navigate",
    [
        "Home",
        "Peer Matching",
        "Practice",
        "Streak",
        "Ratings"
    ]
)

# -------------------------------------------------
# HOME PAGE
# -------------------------------------------------
if page == "Home":
    st.title("Welcome to Adaptive Learning NGO")

    st.markdown("""
    This platform helps students:
    - Find peer learning partners
    - Track daily practice
    - Maintain learning streaks
    - Improve through feedback
    """)

# -------------------------------------------------
# PEER MATCHING PAGE
# -------------------------------------------------
elif page == "Peer Matching":
    st.title("🤝 Peer Learning Matches")

    grade = st.selectbox("Select Grade", ["8", "9", "10", "11", "12"])
    subject = st.selectbox("Select Subject", ["Maths", "Science", "English"])

    if st.button("Find Matches"):
        matches = get_peer_matches(grade, subject)

        if matches:
            for match in matches:
                st.success(
                    f"Matched with {match['name']} "
                    f"(Grade {match['grade']} - {match['subject']})"
                )
        else:
            st.warning("No matches found.")

# -------------------------------------------------
# PRACTICE PAGE
# -------------------------------------------------
elif page == "Practice":
    st.title("📘 Practice Progress")

    user_id = st.session_state.user_id
    practice = get_practice_data(user_id)

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Questions Attempted",
        practice.get("questions_attempted", 0)
    )

    col2.metric(
        "Correct Answers",
        practice.get("correct", 0)
    )

    col3.metric(
        "Accuracy (%)",
        practice.get("accuracy", 0)
    )

# -------------------------------------------------
# STREAK PAGE
# -------------------------------------------------
elif page == "Streak":
    st.title("🔥 Learning Streak")

    user_id = st.session_state.user_id
    streak = get_streak(user_id)

    col1, col2 = st.columns(2)

    col1.metric(
        "Current Streak",
        f"{streak.get('current_streak', 0)} days"
    )

    col2.metric(
        "Longest Streak",
        f"{streak.get('longest_streak', 0)} days"
    )

# -------------------------------------------------
# RATINGS PAGE
# -------------------------------------------------
elif page == "Ratings":
    st.title("⭐ Peer Feedback")

    peer_name = st.text_input("Peer Name")
    rating = st.slider("Rating", 1, 5, 3)
    feedback = st.text_area("Feedback")

    if st.button("Submit Rating"):
        submit_rating(peer_name, rating, feedback)
        st.success("Rating submitted successfully!")

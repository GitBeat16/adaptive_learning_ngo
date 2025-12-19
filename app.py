import streamlit as st
from ratings import show_rating_ui
from matching import find_matches
import time

# -------------------------------
# Session State Initialization
# -------------------------------
if "stage" not in st.session_state:
    st.session_state.stage = 1

if "profile" not in st.session_state:
    st.session_state.profile = {}

if "students" not in st.session_state:
    st.session_state.students = []

if "leaderboard" not in st.session_state:
    st.session_state.leaderboard = {}

if "current_match" not in st.session_state:
    st.session_state.current_match = None

# -------------------------------
# App Title
# -------------------------------
st.title("Peer Learning Matchmaking System")

# =========================================================
# STAGE 1 : PROFILE SETUP
# =========================================================
if st.session_state.stage == 1:
    st.header("Step 1: Profile Setup")

    role = st.radio("Who are you?", ["Student", "Teacher"])
    name = st.text_input("Name")

    time_slot = st.selectbox(
        "Available Time Slot",
        ["4–5 PM", "5–6 PM", "6–7 PM"]
    )

    # Defaults
    year = None
    good_at = []
    weak_at = []
    expertise = []

    if role == "Student":
        year = st.selectbox(
            "Current Year",
            ["First Year (FY)", "Second Year (SY)", "Third Year (TY)", "Fourth Year"]
        )

        good_at = st.multiselect(
            "Strong Subjects",
            ["LAC", "CPPS", "CST", "CGD", "ESE", "IEEE", "IKS", "MFR", "OOPC", "QP"]
        )

        weak_at = st.multiselect(
            "Weak Subjects",
            ["LAC", "CPPS", "CST", "CGD", "ESE", "IEEE", "IKS", "MFR", "OOPC", "QP"]
        )

    else:  # Teacher
        expertise = st.multiselect(
            "Subjects You Teach",
            ["LAC", "CPPS", "CST", "CGD", "ESE", "IEEE", "IKS", "MFR", "OOPC", "QP"]
        )

    if st.button("Submit Profile & Continue"):
        profile = {
            "role": role,
            "name": name,
            "time": time_slot,
            "year": year,
            "good_at": good_at if role == "Student" else expertise,
            "weak_at": weak_at if role == "Student" else []
        }

        st.session_state.profile = profile

        if role == "Student":
            st.session_state.students.append(profile)

        st.session_state.stage = 2
        st.rerun()

# =========================================================
# STAGE 2 : MATCHMAKING
# =========================================================
if st.session_state.stage == 2:
    st.header("Finding the Best Match for You 🎮")

    with st.spinner("Analyzing skills... Comparing profiles..."):
        time.sleep(2)

    matches = find_matches(st.session_state.students)

    if matches:
        best_match = matches[0]
        st.session_state.current_match = best_match

        st.success("Match Found! 🎯")
        st.write(f"**Mentor:** {best_match['Mentor']}")
        st.write(f"**Mentee:** {best_match['Mentee']}")
        st.write(f"**Compatibility Score:** {best_match['Score']}")

        if st.button("Start Learning Session"):
            st.session_state.stage = 3
            st.rerun()
    else:
        st.warning("No suitable match found yet.")
        if st.button("Go Back"):
            st.session_state.stage = 1
            st.rerun()

# =========================================================
# STAGE 3 : LEARNING SESSION
# =========================================================
if st.session_state.stage == 3:
    st.header("Learning Session 💬")

    match = st.session_state.current_match

    st.info(
        f"Mentor: **{match['Mentor']}** | "
        f"Mentee: **{match['Mentee']}** | "
        f"Score: **{match['Score']}**"
    )

    # Chat
    st.subheader("Chat (Prototype)")
    message = st.text_area("Type your doubt")

    if st.button("Send Message"):
        if message.strip():
            st.success("Message sent (prototype)")
        else:
            st.warning("Please type a message")

    st.divider()

    # File Upload & Links
    st.subheader("Share Learning Resources 📎")

    files = st.file_uploader(
        "Upload PDFs or Images",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    if files:
        for f in files:
            st.success(f"Uploaded: {f.name}")

    link = st.text_input("Share a helpful link")
    if link:
        st.info(f"Shared link: {link}")

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Ask AI 🤖"):
            st.info("AI Suggestion (prototype): Revise basics and try stepwise solving.")

    with col2:
        if st.button("Add Faculty 👩‍🏫"):
            st.warning("Faculty notified (prototype)")

    with col3:
        if st.button("Start Video Call 🎥"):
            st.warning("Video call is a prototype (WebRTC integration planned).")

    if st.button("End Session"):
        st.session_state.stage = 4
        st.rerun()

# =========================================================
# STAGE 4 : RATING, BADGES & LEADERBOARD
# =========================================================
if st.session_state.stage == 4:
    st.header("Session Completed 🎉")
    st.write("Rate your mentor")

    show_rating_ui()

    rating = st.session_state.get("rating", 0)

    mentor = st.session_state.current_match["Mentor"]

    # Badges
    if rating == 5:
        st.success("🏅 Gold Mentor Badge Earned!")
    elif rating == 4:
        st.success("🥈 Silver Mentor Badge Earned!")
    elif rating == 3:
        st.success("🥉 Bronze Mentor Badge Earned!")

    # Leaderboard update
    if rating > 0:
        st.session_state.leaderboard[mentor] = (
            st.session_state.leaderboard.get(mentor, 0) + rating * 10
        )

    st.divider()
    st.subheader("🏆 Mentor Leaderboard")

    if st.session_state.leaderboard:
        sorted_board = sorted(
            st.session_state.leaderboard.items(),
            key=lambda x: x[1],
            reverse=True
        )

        for i, (name, points) in enumerate(sorted_board, start=1):
            st.write(f"{i}. {name} — {points} points 🎯")
    else:
        st.info("No mentors rated yet.")

import streamlit as st
import time

# ---- IMPORT PAGES ----
from materials import materials_page
from practice import practice_page
from ratings import show_rating_ui
from matching import find_matches

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Peer Learning Matchmaking System",
    layout="wide"
)

# =========================================================
# SIDEBAR NAVIGATION
# =========================================================
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Matchmaking", "Learning Materials", "Practice"]
)

# =========================================================
# SESSION STATE INITIALIZATION
# =========================================================
if "stage" not in st.session_state:
    st.session_state.stage = 1

if "profile" not in st.session_state:
    st.session_state.profile = {}

# this is REQUIRED for practice_page()
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {}

if "mentors" not in st.session_state:
    st.session_state.mentors = []

if "mentees" not in st.session_state:
    st.session_state.mentees = []

if "leaderboard" not in st.session_state:
    st.session_state.leaderboard = {}

if "current_match" not in st.session_state:
    st.session_state.current_match = None

if "rating" not in st.session_state:
    st.session_state.rating = 0

SUBJECTS = ["Mathematics", "English", "Science"]

# =========================================================
# HELPER FUNCTIONS
# =========================================================
def show_rating_ui():
    st.session_state.rating = st.slider(
        "Rate your mentor (1-5)",
        min_value=0,
        max_value=5,
        value=0,
        step=1
    )

def calculate_match_score(mentee, mentor):
    score = 0
    reasons = []

    mentee_weak = mentee.get("weak_subjects", [])
    mentee_strong = mentee.get("strong_subjects", [])
    mentor_strong = mentor.get("strong_subjects", mentor.get("teaches", []))

    for weak in mentee_weak:
        if weak in mentor_strong:
            score += 50
            reasons.append(f"+50 {weak} help")

    if mentor["time"] == mentee["time"]:
        score += 20
        reasons.append("+20 same time")

    if mentor["grade"] == mentee["grade"]:
        score += 10
        reasons.append("+10 same grade")

    for strong in mentee_strong:
        if strong in mentor_strong:
            score += 5
            reasons.append(f"+5 {strong} practice")

    return score, reasons

def find_best_mentor(mentee, mentors):
    eligible = [m for m in mentors if m["name"] != mentee["name"]]
    best_mentor, best_score, best_reasons = None, -1, []

    for mentor in eligible:
        score, reasons = calculate_match_score(mentee, mentor)
        if score > best_score:
            best_mentor = mentor
            best_score = score
            best_reasons = reasons

    if best_score >= 15:
        return best_mentor, best_score, best_reasons
    return None, 0, []

# =========================================================
# PAGE ROUTING
# =========================================================

# =========================
# PAGE 1: MATCHMAKING
# =========================
if page == "Matchmaking":

    st.title("Peer Learning Matchmaking System")
    st.write("Connect students who excel in subjects with those who need help.")

    # -------------------------------------------------
    # STAGE 1: PROFILE SETUP
    # -------------------------------------------------
    if st.session_state.stage == 1:
        st.header("Create Your Profile")

        role = st.radio("Role", ["Student", "Teacher"])
        name = st.text_input("Full Name")

        grade = st.selectbox("Grade", [f"Grade {i}" for i in range(1, 11)])
        time_slot = st.selectbox("Time Slot", ["4-5 PM", "5-6 PM", "6-7 PM"])

        strong_subjects, weak_subjects, teaches = [], [], []

        if role == "Student":
            col1, col2 = st.columns(2)
            with col1:
                strong_subjects = st.multiselect("Strong Subjects", SUBJECTS)
            with col2:
                weak_subjects = st.multiselect("Weak Subjects", SUBJECTS)
        else:
            teaches = st.multiselect("Subjects You Teach", SUBJECTS)

        if role == "Student" and set(strong_subjects) & set(weak_subjects):
            st.warning("A subject cannot be both strong and weak")

        if st.button("Submit Profile & Find Match", type="primary"):
            if not name.strip():
                st.error("Please enter your name")
            elif role == "Student" and not (strong_subjects or weak_subjects):
                st.error("Select at least one strong or weak subject")
            elif role == "Teacher" and not teaches:
                st.error("Select subjects you teach")
            else:
                profile = {
                    "role": role,
                    "name": name.strip(),
                    "grade": grade,
                    "time": time_slot,
                    "class": int(grade.split()[-1])  # REQUIRED for practice
                }

                if role == "Student":
                    profile["strong_subjects"] = strong_subjects
                    profile["weak_subjects"] = weak_subjects
                    if strong_subjects:
                        st.session_state.mentors.append(profile)
                    if weak_subjects:
                        st.session_state.mentees.append(profile)
                else:
                    profile["teaches"] = teaches
                    st.session_state.mentors.append(profile)

                st.session_state.profile = profile
                st.session_state.user_profile = profile  # PRACTICE PAGE USES THIS
                st.session_state.stage = 2
                st.rerun()

    # -------------------------------------------------
    # STAGE 2: MATCH RESULTS
    # -------------------------------------------------
    if st.session_state.stage == 2:
        st.header("Step 2: Match Results")

        with st.spinner("Finding best mentor..."):
            time.sleep(1)
            mentor, score, reasons = find_best_mentor(
                st.session_state.profile,
                st.session_state.mentors
            )

        if mentor:
            st.success(f"Match Found! Score: {score}")
            st.info("Reasons: " + "; ".join(reasons))

            st.session_state.current_match = {
                "Mentor": mentor["name"],
                "Mentee": st.session_state.profile["name"],
                "Score": score
            }

            if st.button("Start Learning Session", type="primary"):
                st.session_state.stage = 3
                st.rerun()
        else:
            st.warning("No suitable match found")
            if st.button("Back"):
                st.session_state.stage = 1
                st.rerun()

    # -------------------------------------------------
    # STAGE 3: SESSION
    # -------------------------------------------------
    if st.session_state.stage == 3:
        st.header("Learning Session")

        msg = st.text_area("Enter your message")
        if st.button("Send Message"):
            st.success("Message sent")

        if st.button("End Session"):
            st.session_state.stage = 4
            st.rerun()

    # -------------------------------------------------
    # STAGE 4: RATING
    # -------------------------------------------------
    if st.session_state.stage == 4:
        st.header("Rate the Session")

        show_rating_ui()

        if st.button("Submit Rating"):
            mentor = st.session_state.current_match["Mentor"]
            st.session_state.leaderboard[mentor] = (
                st.session_state.leaderboard.get(mentor, 0)
                + st.session_state.rating * 20
            )
            st.success("Thank you for your feedback")

        st.subheader("Leaderboard")
        for i, (name, score) in enumerate(
            sorted(
                st.session_state.leaderboard.items(),
                key=lambda x: x[1],
                reverse=True
            ),
            1
        ):
            st.write(f"{i}. {name} - {score} points")

        if st.button("New Session"):
            for key in list(st.session_state.keys()):
                if key != "leaderboard":
                    del st.session_state[key]
            st.session_state.stage = 1
            st.rerun()

# =========================
# PAGE 2: LEARNING MATERIALS
# =========================
elif page == "Learning Materials":
    materials_page()

# =========================
# PAGE 3: PRACTICE
# =========================
elif page == "Practice":
    if "user_profile" not in st.session_state or not st.session_state.user_profile:
        st.warning("Please create a profile first to access practice questions.")
    else:
        practice_page()

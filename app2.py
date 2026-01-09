import streamlit as st
from ratings import show_rating_ui
from matching import find_matches
import time
st.set_page_config(page_title="Peer Learning Matchmaking System")

# -------------------------------------------------
# Session State Initialization
# -------------------------------------------------
if "stage" not in st.session_state:
    st.session_state.stage = 1

if "profile" not in st.session_state:
    st.session_state.profile = {}

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

# -------------------------------------------------
# Helper functions
# -------------------------------------------------
def show_rating_ui():
    st.session_state.rating = st.slider(
        "Rate your mentor (1-5 stars)",
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
            reasons.append(f"+50: {weak} help")
    
    if mentor["time"] == mentee["time"]:
        score += 20
        reasons.append("+20: same time")
    
    if mentor["grade"] == mentee["grade"]:
        score += 10
        reasons.append("+10: same grade")
    
    for strong in mentee_strong:
        if strong in mentor_strong:
            score += 5
            reasons.append(f"+5: {strong} practice")
    
    return score, reasons

def find_best_mentor(mentee, mentors):
    mentee_name = mentee["name"]
    eligible_mentors = [m for m in mentors if m["name"] != mentee_name]
    
    if not eligible_mentors:
        return None, 0, []
    
    best_mentor = None
    best_score = -1
    best_reasons = []
    
    for mentor in eligible_mentors:
        score, reasons = calculate_match_score(mentee, mentor)
        if score > best_score:
            best_score = score
            best_mentor = mentor
            best_reasons = reasons
    
    return best_mentor, best_score, best_reasons if best_score >= 15 else (None, 0, [])

# -------------------------------------------------
# App Title
# -------------------------------------------------
st.title("Peer Learning Matchmaking System")
st.write("Connect students who excel in subjects with those who need help.")

# =========================================================
# STAGE 1: Profile Setup
# =========================================================
if st.session_state.stage == 1:
    st.header("Step 1: Create Profile")

    role = st.radio("Role", ["Student", "Teacher"])
    name = st.text_input("Full Name", help="Enter your full name")

    grade = st.selectbox("Grade", [f"Grade {i}" for i in range(1, 11)])

    time_slot = st.selectbox("Time Slot", ["4-5 PM", "5-6 PM", "6-7 PM"])

    strong_subjects = []
    weak_subjects = []
    teaches = []

    if role == "Student":
        st.subheader("Subjects")
        col1, col2 = st.columns(2)
        with col1:
            strong_subjects = st.multiselect(
                "Strong Subjects (you can help others with)",
                SUBJECTS,
                key="strong_student"
            )
        with col2:
            weak_subjects = st.multiselect(
                "Weak Subjects (you need help with)",
                SUBJECTS,
                key="weak_student"
            )
    else:
        teaches = st.multiselect(
            "Subjects You Teach/Help With",
            SUBJECTS,
            key="teaches_teacher"
        )

    # STRONG ≠ WEAK VALIDATION
    if role == "Student" and set(strong_subjects) & set(weak_subjects):
        st.warning(
            "Cannot select same subject as both strong AND weak. "
            f"Overlap found: {list(set(strong_subjects) & set(weak_subjects))}"
        )

    if st.button("Submit Profile & Find Match", type="primary"):
        if not name.strip():
            st.error("Please enter your name.")
        elif role == "Student" and not (strong_subjects or weak_subjects):
            st.error("Please select at least one strong or weak subject.")
        elif role == "Teacher" and not teaches:
            st.error("Please select subjects you teach.")
        elif role == "Student" and set(strong_subjects) & set(weak_subjects):
            st.error("Fix subject overlap first.")
        else:
            profile = {
                "role": role,
                "name": name.strip(),
                "grade": grade,
                "time": time_slot,
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
            st.success("Profile created successfully!")
            st.session_state.stage = 2
            st.rerun()

# =========================================================
# STAGE 2: Matching Results
# =========================================================
if st.session_state.stage == 2:
    st.header("Step 2: Match Results")

    current_mentee = st.session_state.profile

    with st.spinner("Analyzing profiles for best match..."):
        time.sleep(1)
        best_mentor, score, reasons = find_best_mentor(current_mentee, st.session_state.mentors)

    # Debug info (collapsible)
    with st.expander("View Match Analysis"):
        st.write("**Your needs**:")
        st.write(f"- Weak subjects: {current_mentee.get('weak_subjects', 'None')}")
        st.write(f"- Strong subjects: {current_mentee.get('strong_subjects', 'None')}")
        st.write(f"- Grade: {current_mentee['grade']}, Time: {current_mentee['time']}")
        
        st.write("**All available mentors & scores**:")
        for mentor in st.session_state.mentors:
            if mentor["name"] != current_mentee["name"]:
                m_score, m_reasons = calculate_match_score(current_mentee, mentor)
                st.write(f"{mentor['name']} ({mentor['role']}): **{m_score}** pts - {m_reasons}")

    if best_mentor and score > 0:
        st.session_state.current_match = {
            "Mentor": best_mentor["name"],
            "Mentee": current_mentee["name"],
            "Grade": current_mentee["grade"],
            "Mentor_Role": best_mentor["role"],
            "Score": score,
            "Reasons": reasons,
        }

        st.success(f"Match Found! Compatibility Score: {score}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Mentor", best_mentor["name"])
            st.metric("Your Role", "Mentee")
        with col2:
            st.metric("Score", score)
            st.metric("Grade", current_mentee["grade"])
        
        st.info("Match reasons: " + "; ".join(reasons))
        
        if st.button("Start Learning Session", type="primary"):
            st.session_state.stage = 3
            st.rerun()
    else:
        st.warning("No suitable match found.")
        st.info("Try registering more strong students or teachers.")
        if st.button("Back to Profile"):
            st.session_state.stage = 1
            st.rerun()

# =========================================================
# STAGE 3: Learning Session
# =========================================================
if st.session_state.stage == 3:
    st.header("Learning Session")

    match = st.session_state.current_match
    st.info(
        f"Mentor: {match['Mentor']} ({match['Mentor_Role']}) | "
        f"Mentee: {match['Mentee']} | Score: {match['Score']}"
    )

    st.subheader("Chat")
    message = st.text_area("Enter your question or message")
    if st.button("Send Message"):
        if message.strip():
            st.success("Message sent")
        else:
            st.warning("Please enter a message")

    st.subheader("Share Resources")
    files = st.file_uploader("Upload files", type=['pdf', 'png', 'jpg'], accept_multiple_files=True)
    if files:
        for f in files:
            st.success(f"Uploaded: {f.name}")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("AI Assistance"):
            st.info("Consider breaking problems into smaller steps.")
    with col2:
        if st.button("Share Progress"):
            st.success("Progress shared")
    with col3:
        if st.button("End Session"):
            st.session_state.stage = 4
            st.rerun()

# =========================================================
# STAGE 4: Rating
# =========================================================
if st.session_state.stage == 4:
    st.header("Rate Your Session")

    show_rating_ui()
    rating = st.session_state.rating
    mentor_name = st.session_state.current_match["Mentor"]

    if st.button("Submit Rating"):
        if rating > 0:
            st.session_state.leaderboard[mentor_name] = (
                st.session_state.leaderboard.get(mentor_name, 0) + rating * 20
            )
            st.success("Thank you for your feedback!")
        else:
            st.warning("Please select a rating")

    st.subheader("Leaderboard")
    if st.session_state.leaderboard:
        sorted_leaderboard = sorted(st.session_state.leaderboard.items(), 
                                  key=lambda x: x[1], reverse=True)
        for i, (name, score) in enumerate(sorted_leaderboard[:5], 1):
            st.write(f"{i}. {name}: {score} points")

    if st.button("New Session"):
        for key in list(st.session_state.keys()):
            if key not in ["leaderboard"]:
                del st.session_state[key]
        st.session_state.stage = 1
        st.rerun()

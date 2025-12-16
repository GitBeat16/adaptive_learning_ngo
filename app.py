import streamlit as st

# Initialize storage
if "students" not in st.session_state:
    st.session_state.students = []

st.title("Peer Learning Matchmaking System")

st.header("Student Skill Form")

name = st.text_input("Student Name")

good_at = st.multiselect(
    "Good At",
    ["LAC", "CPPS", "CST", "CGD", "ESE", "IEEE", "IKS", "MFR", "OOPC", "QP"]
)

needs_help = st.multiselect(
    "Needs Help In",
    ["LAC", "CPPS", "CST", "CGD", "ESE", "IEEE", "IKS", "MFR", "OOPC", "QP"]
)

time = st.selectbox(
    "Available Time Slot",
    ["4–5 PM", "5–6 PM", "6–7 PM"]
)

if st.button("Submit"):
    st.session_state.students.append({
        "name": name,
        "good_at": good_at,
        "needs_help": needs_help,
        "time": time
    })
    st.success("Profile added successfully!")

st.subheader("Stored Student Profiles")
st.write(st.session_state.students)

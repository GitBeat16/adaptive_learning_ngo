import streamlit as st

# =========================================================
# PAGE CONFIG (MUST BE FIRST)
# =========================================================
st.set_page_config(
    page_title="Sahay | Peer Learning Matchmaking",
    layout="wide"
)

from datetime import date

# ---- IMPORT PAGES (AFTER set_page_config) ----
from materials import materials_page
from practice import practice_page
from admin import admin_page
from auth import auth_page
from dashboard import dashboard_page
from matching import matchmaking_page

# ---- DATABASE ----
from database import init_db

# =========================================================
# GLOBAL UI STYLES
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins','Inter','Segoe UI',sans-serif;
}

/* App background */
.stApp {
    background: linear-gradient(135deg,#f5f7fa,#eef1f5);
}

/* Sidebar */
section[data-testid="stSidebar"] {
  background: rgba(255,255,255,0.9);
  backdrop-filter: blur(12px);
  border-right: 1px solid rgba(200,200,200,0.3);
}

/* ================= SAHAY TITLE (ONLY THIS CHANGED) ================= */
.sidebar-header {
  padding:1.6rem;
  border-radius:20px;
  background:
    radial-gradient(circle at top left, #818cf8, #6366f1 40%, #4f46e5);
  color:white;
  margin-bottom:1.4rem;
  text-align:center;
  box-shadow:0 12px 30px rgba(79,70,229,0.45);
}

.sidebar-header .app-name {
  font-size:2.6rem;
  font-weight:800;
  letter-spacing:0.04em;
}

.sidebar-header .username {
  margin-top:0.4rem;
  font-size:0.95rem;
  opacity:0.9;
}

/* Cards */
.card {
  background: rgba(255,255,255,.95);
  border-radius:20px;
  padding:1.8rem;
  box-shadow:0 12px 30px rgba(0,0,0,.06);
}

/* ================= PURPLE BUTTON SYSTEM ================= */
/* Applies everywhere EXCEPT sidebar nav buttons logic-wise */
.stApp .stButton > button {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg,#6366f1,#4f46e5);
  color: #ffffff;
  border: none;
  border-radius: 999px;
  padding: 0.55rem 1.1rem;
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  box-shadow: 0 6px 18px rgba(79,70,229,0.35);
}

/* Hover */
.stApp .stButton > button:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 28px rgba(79,70,229,0.45);
  background: linear-gradient(135deg,#4f46e5,#4338ca);
}

/* Ripple */
.stApp .stButton > button::after {
  content:"";
  position:absolute;
  top:50%;
  left:50%;
  width:8px;
  height:8px;
  background:rgba(255,255,255,0.5);
  border-radius:50%;
  transform:translate(-50%,-50%) scale(0);
  opacity:0;
}

.stApp .stButton > button:active::after {
  animation:ripple 0.6s ease-out;
}

@keyframes ripple {
  0% {
    transform:translate(-50%,-50%) scale(0);
    opacity:0.7;
  }
  100% {
    transform:translate(-50%,-50%) scale(18);
    opacity:0;
  }
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# SESSION STATE INIT
# =========================================================
for key, default in {
    "logged_in": False,
    "user_id": None,
    "user_name": "",
    "page": "Dashboard",
    "proposed_match": None,
    "proposed_score": None
}.items():
    st.session_state.setdefault(key, default)

# =========================================================
# AUTH GATE
# =========================================================
if not st.session_state.logged_in:
    auth_page()
    st.stop()

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-header">
        <div class="app-name">Sahay</div>
        <div class="username">{st.session_state.user_name}</div>
    </div>
    """, unsafe_allow_html=True)

    for label in [
        "Dashboard",
        "Matchmaking",
        "Learning Materials",
        "Practice",
        "Donations",
        "Admin"
    ]:
        if st.button(label, use_container_width=True):
            st.session_state.page = label
            st.rerun()

    st.divider()

    if st.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# =========================================================
# ROUTING
# =========================================================
page = st.session_state.page

if page == "Dashboard":
    dashboard_page()

elif page == "Matchmaking":
    matchmaking_page()

elif page == "Learning Materials":
    materials_page()

elif page == "Practice":
    practice_page()

elif page == "Donations":
    st.markdown("<div class='card'><h2>Support Education</h2></div>", unsafe_allow_html=True)

elif page == "Admin":
    key = st.text_input("Admin Access Key", type="password")
    if key == "ngo-admin-123":
        admin_page()

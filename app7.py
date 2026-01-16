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
# ❗ DO NOT call init_db() here (already auto-called in database.py)
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

.stApp {
    background: linear-gradient(135deg,#f5f7fa,#eef1f5);
}

section[data-testid="stSidebar"] {
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(12px);
  border-right: 1px solid rgba(200,200,200,0.3);
}

.sidebar-header {
  padding:1.4rem;
  border-radius:18px;
  background:linear-gradient(135deg,#6366f1,#4f46e5);
  color:white;
  margin-bottom:1.2rem;
  text-align:center;
}

.card {
  background: rgba(255,255,255,.95);
  border-radius:20px;
  padding:1.8rem;
  box-shadow:0 12px 30px rgba(0,0,0,.06);
}

.donate-btn {
  display:block;
  width:100%;
  padding:0.9rem 1rem;
  margin-top:1rem;
  border-radius:999px;
  text-align:center;
  font-weight:700;
  font-size:0.95rem;
  color:#ffffff !important;
  background:linear-gradient(135deg,#6366f1,#4f46e5);
  text-decoration:none;
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
        <div style="font-size:2.4rem;font-weight:700;">Sahay</div>
        <div style="margin-top:0.45rem;font-size:0.95rem;">
            {st.session_state.user_name}
        </div>
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
    st.markdown("<div class='card'><h2>🤝 Support Education</h2></div>", unsafe_allow_html=True)

elif page == "Admin":
    key = st.text_input("Admin Access Key", type="password")
    if key == "ngo-admin-123":
        admin_page()

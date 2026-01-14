import streamlit as st
from datetime import date

# ---- IMPORT PAGES ----
from materials import materials_page
from practice import practice_page
from admin import admin_page
from auth import auth_page
from dashboard import dashboard_page
from matching import matchmaking_page

# ---- DATABASE ----
from database import init_db

# =========================================================
# INIT DATABASE
# =========================================================
init_db()

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Sahay | Peer Learning Matchmaking",
    layout="wide"
)

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
  background: rgba(255,255,255,.92);
  border-radius:18px;
  padding:1.6rem;
  box-shadow:0 12px 30px rgba(0,0,0,.06);
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
    if key not in st.session_state:
        st.session_state[key] = default

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
        <div style="font-size:2.4rem;font-weight:700;">
            Sahay
        </div>
        <div style="margin-top:0.45rem;font-size:0.95rem;">
            {st.session_state.user_name}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Navigation
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
    st.markdown("""
    <div class="card">
        <h2>🤝 Support Education & Nutrition</h2>
        <p>
            Your contribution can help educate children, provide nutritious meals,
            and empower communities across India.
            Choose a trusted NGO below to make a difference.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="card">
            <h4>Pratham</h4>
            <p>Improving learning outcomes for children across India.</p>
            <a href="https://pratham.org/donation/" target="_blank">
                <button style="width:100%">Donate</button>
            </a>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="card">
            <h4>Akshaya Patra</h4>
            <p>Providing mid-day meals to millions of school children.</p>
            <a href="https://www.akshayapatra.org/onlinedonations" target="_blank">
                <button style="width:100%">Donate</button>
            </a>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="card">
            <h4>Teach For India</h4>
            <p>Building a movement to eliminate educational inequity.</p>
            <a href="https://www.teachforindia.org/donate" target="_blank">
                <button style="width:100%">Donate</button>
            </a>
        </div>
        """, unsafe_allow_html=True)

elif page == "Admin":
    key = st.text_input("Admin Access Key", type="password")
    if key == "ngo-admin-123":
        admin_page()

import streamlit as st
from datetime import date

# =========================================================
# PAGE CONFIG (MUST BE FIRST)
# =========================================================
st.set_page_config(
    page_title="Sahay | Peer Learning Matchmaking",
    layout="wide"
)

# =========================================================
# IMPORT PAGES
# =========================================================
from materials import materials_page
from practice import practice_page
from admin import admin_page
from matching import matchmaking_page

# =========================================================
# DATABASE
# =========================================================
from database import init_db
init_db()

# =========================================================
# GLOBAL UI STYLES
# =========================================================
st.markdown("""
<style>
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
  text-align:center;
}

.card {
  background: rgba(255,255,255,.95);
  border-radius:20px;
  padding:1.8rem;
  box-shadow:0 12px 30px rgba(0,0,0,.06);
}

/* Donate Button */
.donate-btn {
  display:block;
  width:100%;
  padding:0.9rem 1rem;
  border-radius:14px;
  text-align:center;
  font-weight:700;
  font-size:0.95rem;
  color:#ffffff !important;
  text-decoration:none !important;
  background:linear-gradient(135deg,#6366f1,#4f46e5);
  transition:all 0.25s ease;
}

.donate-btn:hover {
  transform:translateY(-2px);
  box-shadow:0 10px 25px rgba(79,70,229,.35);
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# SESSION STATE DEFAULTS
# =========================================================
defaults = {
    "authenticated": False,
    "user_id": None,
    "user_name": "Guest",
    "page": "Matchmaking",
    "current_match": None,
    "proposed_match": None,
    "proposed_score": None
}

for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# =========================================================
# AUTH GATE
# =========================================================
if not st.session_state.authenticated:
    st.warning("Please log in to continue.")
    st.stop()

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-header">
        <div style="font-size:2.2rem;font-weight:700;">Sahay</div>
        <div style="margin-top:0.4rem;font-size:0.95rem;">
            {st.session_state.user_name}
        </div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        ["Matchmaking", "Materials", "Practice", "Donations", "Admin"],
        index=0
    )

# =========================================================
# PAGE ROUTING
# =========================================================
if page == "Matchmaking":
    matchmaking_page()

elif page == "Materials":
    materials_page()

elif page == "Practice":
    practice_page()

elif page == "Donations":

    st.markdown("""
    <div class="card">
        <h2>Support Education & Nutrition</h2>
        <p>Your contribution helps children learn better and stay nourished.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="card">
            <h4>Pratham</h4>
            <p>Improving foundational learning outcomes.</p>
            <a class="donate-btn" href="https://pratham.org/donation/" target="_blank">
                Donate
            </a>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="card">
            <h4>Akshaya Patra</h4>
            <p>Ensuring no child studies hungry.</p>
            <a class="donate-btn" href="https://www.akshayapatra.org/onlinedonations" target="_blank">
                Donate
            </a>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="card">
            <h4>Teach For India</h4>
            <p>Eliminating educational inequity.</p>
            <a class="donate-btn" href="https://www.teachforindia.org/donate" target="_blank">
                Donate
            </a>
        </div>
        """, unsafe_allow_html=True)

elif page == "Admin":
    key = st.text_input("Admin Access Key", type="password")
    admin_page(key)

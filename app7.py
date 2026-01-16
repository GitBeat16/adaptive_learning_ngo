import streamlit as st

# =========================================================
# PAGE CONFIG (MUST BE FIRST)
# =========================================================
st.set_page_config(
    page_title="Sahay | Peer Learning Matchmaking",
    layout="wide"
)

from datetime import date

# ---- IMPORT PAGES ----
# ---- IMPORT PAGES (AFTER set_page_config) ----
from materials import materials_page
from practice import practice_page
from admin import admin_page
@@ -10,21 +19,9 @@
from matching import matchmaking_page

# ---- DATABASE ----
# ❗ DO NOT call init_db() here (already auto-called in database.py)
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
@@ -36,19 +33,16 @@
    font-family: 'Poppins','Inter','Segoe UI',sans-serif;
}

/* App background */
.stApp {
    background: linear-gradient(135deg,#f5f7fa,#eef1f5);
}

/* Sidebar */
section[data-testid="stSidebar"] {
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(12px);
  border-right: 1px solid rgba(200,200,200,0.3);
}

/* Sidebar header */
.sidebar-header {
  padding:1.4rem;
  border-radius:18px;
@@ -58,18 +52,14 @@
  text-align:center;
}

/* Cards */
.card {
  background: rgba(255,255,255,.95);
  border-radius:20px;
  padding:1.8rem;
  box-shadow:0 12px 30px rgba(0,0,0,.06);
}

/* ================= DONATE BUTTON ================= */
.donate-btn {
  position:relative;
  overflow:hidden;
  display:block;
  width:100%;
  padding:0.9rem 1rem;
@@ -78,49 +68,9 @@
  text-align:center;
  font-weight:700;
  font-size:0.95rem;

  color:#ffffff !important;
  text-decoration:none !important;

  background:linear-gradient(135deg,#6366f1,#4f46e5);
  cursor:pointer;
  transition:transform 0.25s ease, box-shadow 0.25s ease;
}

/* Hover */
.donate-btn:hover {
  transform:translateY(-2px);
  box-shadow:0 10px 25px rgba(79,70,229,.35);
  background:linear-gradient(135deg,#4f46e5,#4338ca);
}

/* ================= RIPPLE EFFECT ================= */
.donate-btn::after {
  content:"";
  position:absolute;
  top:50%;
  left:50%;
  width:10px;
  height:10px;
  background:rgba(255,255,255,0.45);
  border-radius:50%;
  transform:translate(-50%,-50%) scale(0);
  opacity:0;
}

.donate-btn:active::after {
  animation:ripple 0.6s ease-out;
}

@keyframes ripple {
  0% {
    transform:translate(-50%,-50%) scale(0);
    opacity:0.7;
  }
  100% {
    transform:translate(-50%,-50%) scale(20);
    opacity:0;
  }
  text-decoration:none;
}
</style>
""", unsafe_allow_html=True)
@@ -136,8 +86,7 @@
    "proposed_match": None,
    "proposed_score": None
}.items():
    if key not in st.session_state:
        st.session_state[key] = default
    st.session_state.setdefault(key, default)

# =========================================================
# AUTH GATE
@@ -150,12 +99,9 @@
# SIDEBAR
# =========================================================
with st.sidebar:

    st.markdown(f"""
    <div class="sidebar-header">
        <div style="font-size:2.4rem;font-weight:700;">
            Sahay
        </div>
        <div style="font-size:2.4rem;font-weight:700;">Sahay</div>
        <div style="margin-top:0.45rem;font-size:0.95rem;">
            {st.session_state.user_name}
        </div>
@@ -198,53 +144,7 @@
    practice_page()

elif page == "Donations":

    st.markdown("""
    <div class="card">
        <h2>🤝 Support Education & Nutrition</h2>
        <p>
            Your contribution helps children learn better, stay nourished,
            and build a brighter future.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="card">
            <h4>Pratham</h4>
            <p>Improving foundational learning outcomes for millions of children.</p>
            <a class="donate-btn" href="https://pratham.org/donation/" target="_blank">
                Donate to Pratham
            </a>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="card">
            <h4>Akshaya Patra</h4>
            <p>Ensuring no child is deprived of education due to hunger.</p>
            <a class="donate-btn" href="https://www.akshayapatra.org/onlinedonations" target="_blank">
                Donate to Akshaya Patra
            </a>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="card">
            <h4>Teach For India</h4>
            <p>Building a movement to eliminate educational inequity.</p>
            <a class="donate-btn" href="https://www.teachforindia.org/donate" target="_blank">
                Donate to Teach For India
            </a>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("<div class='card'><h2>🤝 Support Education</h2></div>", unsafe_allow_html=True)

elif page == "Admin":
    key = st.text_input("Admin Access Key", type="password")

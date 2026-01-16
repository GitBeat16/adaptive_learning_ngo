import streamlit as st
import os
from openai import OpenAI

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Sahay | Peer Learning Matchmaking",
    page_icon="🌱",
    layout="wide"
)

# ---- SECURE OPENAI CLIENT SETUP ----
try:
    # This looks for the key in .streamlit/secrets.toml
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    client = None

# ---- DIRECTORY SETUP ----
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# ---- IMPORT PAGES ----
from materials import materials_page
from practice import practice_page
from admin import admin_page
from auth import auth_page
from dashboard import dashboard_page
from matching import matchmaking_page

# =========================================================
# GLOBAL UI STYLES (EMERALD THEME)
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins','Inter','Segoe UI',sans-serif;
}

.stApp {
    background: linear-gradient(135deg,#f5f7fa,#eef1f5);
}

section[data-testid="stSidebar"] {
  background: rgba(255,255,255,0.9);
  backdrop-filter: blur(12px);
  border-right: 1px solid rgba(200,200,200,0.3);
}

.sidebar-header {
  padding:1.6rem;
  border-radius:20px;
  background: linear-gradient(135deg, #0f766e, #14b8a6, #22c55e);
  color:white;
  margin-bottom:1.4rem;
  text-align:center;
  box-shadow:0 12px 30px rgba(20,184,166,0.45);
}

.sidebar-header .app-name {
  font-size:2.6rem;
  font-weight:800;
  letter-spacing:0.06em;
}

.card {
  background: rgba(255,255,255,.95);
  border-radius:20px;
  padding:1.8rem;
  box-shadow:0 12px 30px rgba(0,0,0,.06);
  margin-bottom: 1.5rem;
}

/* --- EMERALD RIPPLE BUTTONS --- */
.ripple-btn {
    background: #10b981;
    color: white !important;
    padding: 12px 24px;
    border: none;
    border-radius: 12px;
    cursor: pointer;
    font-weight: 600;
    text-decoration: none;
    display: inline-block;
    transition: background 0.5s;
    text-align: center;
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.2);
    width: 100%;
}

.ripple-btn:hover {
    background: #0d9488 radial-gradient(circle, transparent 1%, #0d9488 1%) center/15000%;
    color: white !important;
}

.ripple-btn:active {
    background-color: #0f766e;
    background-size: 100%;
    transition: background 0s;
}

.donation-card {
    background: white; 
    padding: 1.8rem; 
    border-radius: 20px; 
    border-left: 8px solid #10b981; 
    margin-bottom: 1.5rem; 
    box-shadow: 0 8px 20px rgba(0,0,0,0.04);
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
    "messages": [], 
    "session_step": "discovery" 
}.items():
    st.session_state.setdefault(key, default)

# =========================================================
# AUTH GATE
# =========================================================
if not st.session_state.logged_in:
    auth_page()
    st.stop()

# =========================================================
# SIDEBAR NAVIGATION
# =========================================================
with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-header">
        <div class="app-name">Sahay</div>
        <div class="username">{st.session_state.user_name}</div>
    </div>
    """, unsafe_allow_html=True)

    nav_options = ["Dashboard", "Matchmaking", "Learning Materials", "Practice", "AI Assistant", "Donations", "Admin"]

    for label in nav_options:
        if st.button(label, use_container_width=True):
            st.session_state.page = label
            if label != "Matchmaking":
                st.session_state.session_step = "discovery"
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

elif page == "AI Assistant":
    if client is None:
        st.error("OpenAI API Key is missing. Please add it to your secrets.toml file.")
        st.stop()

    col_title, col_clear = st.columns([3, 1])
    with col_title:
        st.markdown("""
            <div class='card'>
                <h1 style='color:#0f766e; margin-bottom:0;'>Sahay AI Assistant</h1>
                <p style='color:#64748b;'>Your emerald-themed learning companion.</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col_clear:
        st.markdown('<br>', unsafe_allow_html=True)
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # Chat Display
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("How can I help you today?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                response_placeholder = st.empty()
                full_response = ""
                
                for response in client.chat.completions.create(
                    model="gpt-3.5-turbo", 
                    messages=[
                        {"role": "system", "content": "You are Sahay AI, a helpful mentor for a peer-learning platform."},
                        *[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                    ],
                    stream=True,
                ):
                    full_response += (response.choices[0].delta.content or "")
                    response_placeholder.markdown(full_response + "▌")
                
                response_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"Error: {e}")

elif page == "Donations":
    st.markdown("<div class='card'><h1 style='color:#0f766e;'>Support Education</h1>

import streamlit as st
import os
from openai import OpenAI

# =========================================================
# PAGE CONFIG (MUST BE FIRST)
# =========================================================
st.set_page_config(
    page_title="Sahay | Peer Learning Matchmaking",
    page_icon="🌱",
    layout="wide"
)

# ---- OPENAI CLIENT SETUP ----
# Replace with your actual key or use st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key="YOUR_OPENAI_API_KEY")

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

/* --- DONATION & BOT ELEMENTS --- */
.donation-card {
    background: white; 
    padding: 1.8rem; 
    border-radius: 20px; 
    border-left: 8px solid #10b981; 
    margin-bottom: 1.5rem; 
    box-shadow: 0 8px 20px rgba(0,0,0,0.04);
}

.ripple-btn {
    background: #10b981;
    color: white !important;
    padding: 14px 28px;
    border-radius: 12px;
    cursor: pointer;
    font-weight: 600;
    text-decoration: none;
    display: inline-block;
    transition: background 0.5s;
    text-align: center;
}

.ripple-btn:hover {
    background: #0d9488 radial-gradient(circle, transparent 1%, #0d9488 1%) center/15000%;
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

    nav_options = [
        "Dashboard",
        "Matchmaking",
        "Learning Materials",
        "Practice",
        "AI Assistant",
        "Donations",
        "Admin"
    ]

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
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("""
            <div class='card'>
                <h1 style='color:#0f766e; margin-bottom:0;'>Sahay AI Bot</h1>
                <p style='color:#64748b;'>Powered by OpenAI</p>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input logic with OpenAI
    if prompt := st.chat_input("Ask me about your studies..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                # API Call to OpenAI
                stream = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are Sahay AI, a helpful assistant for a peer learning platform. Use an encouraging tone."},
                        *[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                    ],
                    stream=True,
                )
                response = st.write_stream(stream)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"Error connecting to OpenAI: {e}")

elif page == "Donations":
    st.markdown("<div class='card'><h1 style='color:#0f766e;'>Support Education</h1></div>", unsafe_allow_html=True)
    
    donations = [
        {"name": "Pratham", "url": "https://pratham.org/donation/", "desc": "Addressing gaps in the education system.", "icon": '<svg viewBox="0 0 24 24" width="40" height="40" stroke="#0f766e" stroke-width="2" fill="none"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path></svg>'},
        {"name": "Akshaya Patra", "url": "https://www.akshayapatra.org/onlinedonations", "desc": "Eliminating classroom hunger.", "icon": '<svg viewBox="0 0 24 24" width="40" height="40" stroke="#0f766e" stroke-width="2" fill="none"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>'},
        {"name": "Teach For India", "url": "https://www.teachforindia.org/donate", "desc": "Eliminating educational inequity.", "icon": '<svg viewBox="0 0 24 24" width="40" height="40" stroke="#0f766e" stroke-width="2" fill="none"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>'}
    ]

    for org in donations:
        st.markdown(f"""
        <div class="donation-card">
            <div style="display: flex; align-items: center; gap: 20px; margin-bottom:15px;">
                {org['icon']}
                <div>
                    <h3 style="margin:0; color:#0f766e;">{org['name']}</h3>
                    <p style="margin:0; color:#4b5563; font-size:0.9rem;">{org['desc']}</p>
                </div>
            </div>
            <a href="{org['url']}" target="_blank" class="ripple-btn">Donate Now →</a>
        </div>
        """, unsafe_allow_html=True)

elif page == "Admin":
    key = st.text_input("Admin Access Key", type="password")
    if key == "ngo-admin-123":
        admin_page()

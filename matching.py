import streamlit as st
import time
import os
import requests
from database import conn

# Defensive Import for Animations
try:
    from streamlit_lottie import st_lottie
    LOTTIE_AVAILABLE = True
except ImportError:
    LOTTIE_AVAILABLE = False

# =========================================================
# THEME & VECTOR STYLING
# =========================================================
def inject_ui():
    st.markdown("""
        <style>
        /* Modern Emerald Theme - No top gap */
        .block-container { padding-top: 1rem !important; }
        
        .sahay-card {
            background: #ffffff;
            border: 2px solid #10b981;
            border-radius: 24px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(16, 185, 129, 0.1);
            margin-bottom: 20px;
        }

        /* Vector-Style Buttons */
        div.stButton > button {
            background: linear-gradient(135deg, #10b981, #059669) !important;
            color: white !important;
            border-radius: 12px !important;
            border: none !important;
            font-weight: 700 !important;
            height: 3.5rem !important;
        }
        
        .ai-sidebar {
            background: #f0fdf4;
            border-radius: 24px;
            padding: 20px;
            border: 1px solid #bbf7d0;
        }
        </style>
    """, unsafe_allow_html=True)

# Helper to load vector animations correctly
@st.cache_data
def load_lottie_json(url):
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.json() # Returns the actual JSON data
        return None
    except:
        return None

# =========================================================
# PEER DISCOVERY LOGIC
# =========================================================

def show_discovery():
    st.markdown("### 💠 Peer Matchmaking")
    st.write("Find a compatible study partner using our AI matching system.")
    
    if st.button("Search Compatible Partner"):
        st.session_state.searching = True

    if st.session_state.get("searching"):
        # Correctly passing JSON data to st_lottie
        lottie_url = "https://assets5.lottiefiles.com/packages/lf20_6p8yjc2y.json"
        lottie_json = load_lottie_json(lottie_url)
        
        if LOTTIE_AVAILABLE and lottie_json:
            st_lottie(lottie_json, height=200, key="radar")
        else:
            st.info("💠 Scanning active nodes...")
        
        time.sleep(2)
        peer = conn.execute("""
            SELECT p.user_id, a.name, p.grade 
            FROM profiles p 
            JOIN auth_users a ON a.id = p.user_id 
            WHERE p.status = 'waiting' AND p.user_id != ? LIMIT 1
        """, (st.session_state.user_id,)).fetchone()
        
        if peer:
            st.session_state.found_peer = {"id": peer[0], "name": peer[1], "grade": peer[2]}
            st.session_state.searching = False
            st.rerun()
        else:
            st.session_state.searching = False
            st.warning("No peers found. Please try again.")

    # THE PEER CARD (Appears after search)
    if "found_peer" in st.session_state and st.session_state.found_peer:
        p = st.session_state.found_peer
        st.markdown(f"""
            <div class="sahay-card" style="text-align: center;">
                <div style="font-size:24px; font-weight:800; color:#064e3b;">{p['name']}</div>
                <div style="color:#059669; font-weight:500;">Grade {p['grade']}</div>
            </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Accept & Connect"):
                st.balloons()
                st.session_state.session_step = "live"
                st.rerun()
        with c2:
            if st.button("Decline", type="secondary"):
                del st.session_state.found_peer
                st.rerun()

# =========================================================
# MAIN PAGE ROUTER
# =========================================================
def matchmaking_page():
    inject_ui()
    
    if "session_step" not in st.session_state:
        st.session_state.session_step = "discovery"

    # Using columns for 70/30 split to keep AI Assistant visible
    main_col, ai_col = st.columns([2, 1], gap="medium")
    
    with main_col:
        if st.session_state.session_step == "discovery":
            show_discovery()
        elif st.session_state.session_step == "live":
            st.markdown("### 💠 Collaborative Session")
            st.success(f"You are now live with your partner.")
            if st.button("End Session"):
                st.session_state.session_step = "discovery"
                st.rerun()

    with ai_col:
        st.markdown("<div class='ai-sidebar'>", unsafe_allow_html=True)
        st.markdown("#### 💠 Sahay AI Assistant")
        st.caption("Monitoring active for real-time support.")
        st.divider()
        st.info("Ask me to summarize your chat or explain a concept anytime.")
        st.markdown("</div>", unsafe_allow_html=True)

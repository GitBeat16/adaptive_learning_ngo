import streamlit as st
import time
import os
import json
import requests
from database import conn

# =========================================================
# LOTTE ANIMATION LOADER
# =========================================================
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# Vector Art Animations
lottie_search = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_6p8yjc2y.json") # Radar Search
lottie_success = load_lottieurl("https://assets3.lottiefiles.com/packages/lf20_pqnfmone.json") # Connection Confirmed

# =========================================================
# THEME & BUTTON STYLING (SAHAY EMERALD)
# =========================================================
def inject_ui():
    st.markdown("""
        <style>
        /* Modernized Layout */
        .block-container { padding-top: 1.5rem !important; }
        
        /* Peer Detail Card - Clean Vector Style */
        .peer-card {
            background: #ffffff;
            border: 2px solid #10b981;
            border-radius: 24px;
            padding: 30px;
            text-align: center;
            box-shadow: 0 15px 35px rgba(16, 185, 129, 0.08);
            margin: 25px 0;
            transition: all 0.3s ease;
        }
        .peer-name { color: #064e3b; font-size: 26px; font-weight: 800; }
        .peer-meta { color: #059669; font-weight: 500; font-size: 15px; margin-bottom: 20px; }

        /* Unified Button Theme */
        div.stButton > button {
            background: linear-gradient(135deg, #10b981, #059669) !important;
            color: white !important;
            border-radius: 14px !important;
            border: none !important;
            font-weight: 700 !important;
            height: 3.5rem !important;
            transition: 0.3s;
        }
        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(16, 185, 129, 0.3) !important;
        }
        
        /* Glassmorphism AI Box */
        .ai-panel {
            background: rgba(240, 253, 244, 0.8);
            backdrop-filter: blur(5px);
            border-radius: 24px;
            padding: 25px;
            border: 1px solid #bbf7d0;
            min-height: 550px;
        }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# MATCHMAKING PHASES
# =========================================================

def show_discovery():
    from streamlit_lottie import st_lottie # Ensure this is installed
    
    st.markdown("### 💠 Peer Matchmaking")
    st.write("Connect with a compatible peer through our vector-optimized matching network.")
    
    # 1. THE SEARCH BUTTON
    if st.button("Search Compatible Partner"):
        st.session_state.searching = True

    if st.session_state.get("searching"):
        st_lottie(lottie_search, height=200, key="searching_anim")
        time.sleep(2)
        
        peer = conn.execute("""
            SELECT p.user_id, a.name, p.grade, p.strong_subjects 
            FROM profiles p 
            JOIN auth_users a ON a.id = p.user_id 
            WHERE p.status = 'waiting' AND p.user_id != ? LIMIT 1
        """, (st.session_state.user_id,)).fetchone()
        
        if peer:
            st.session_state.found_peer = {
                "id": peer[0], "name": peer[1], 
                "grade": peer[2], "subjects": peer[3]
            }
            st.session_state.searching = False
            st.rerun()
        else:
            st.session_state.searching = False
            st.info("System: Scanning active nodes... No peers found yet.")

    # 2. THE PEER DETAIL CARD
    if "found_peer" in st.session_state and st.session_state.found_peer:
        p = st.session_state.found_peer
        st.markdown(f"""
            <div class="peer-card">
                <div class="peer-name">{p['name']}</div>
                <div class="peer-meta">Grade {p['grade']} • Specializes in {p['subjects']}</div>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Connect Now"):
                m_id = f"sess_{int(time.time())}"
                st.session_state.current_match_id = m_id
                st.session_state.peer_info = p
                
                # DB Sync
                conn.execute("UPDATE profiles SET status='confirming', match_id=?, accepted=1 WHERE user_id=?", (m_id, st.session_state.user_id))
                conn.execute("UPDATE profiles SET status='confirming', match_id=?, accepted=0 WHERE user_id=?", (m_id, p['id']))
                conn.commit()
                
                st.session_state.show_success = True
                st.rerun()
        
        with col2:
            if st.button("Cancel Search"):
                del st.session_state.found_peer
                st.rerun()

def show_success_step():
    from streamlit_lottie import st_lottie
    st_lottie(lottie_success, height=300)
    st.markdown("<h2 style='text-align: center; color: #10b981;'>💠 Connection Established</h2>", unsafe_allow_html=True)
    time.sleep(2)
    st.session_state.session_step = "live"
    st.session_state.show_success = False
    st.rerun()

def show_live_session():
    st.markdown(f"### 💠 Collaborative Session: {st.session_state.peer_info['name']}")
    
    chat_container = st.container(height=350, border=True)
    with chat_container:
        st.caption("Secure Peer Connection Verified")
    
    with st.form("msg_form", clear_on_submit=True):
        col_txt, col_btn = st.columns([5, 1])
        msg = col_txt.text_input("Enter message", label_visibility="collapsed")
        if col_btn.form_submit_button("Send"):
            pass
    
    if st.button("Terminate Session"):
        st.session_state.session_step = "discovery"
        if "found_peer" in st.session_state: del st.session_state.found_peer
        st.rerun()

# =========================================================
# MAIN ROUTER
# =========================================================
def matchmaking_page():
    inject_ui()
    
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"

    col_left, col_right = st.columns([2, 1], gap="large")
    
    with col_left:
        if st.session_state.get("show_success"):
            show_success_step()
        elif st.session_state.session_step == "discovery":
            show_discovery()
        elif st.session_state.session_step == "live":
            show_live_session()

    with col_right:
        st.markdown("<div class='ai-panel'>", unsafe_allow_html=True)
        st.markdown("#### 💠 Sahay AI Assistant")
        st.write("Contextual monitoring is active. I can provide definitions or summaries upon request.")
        st.divider()
        st.text_area("AI Workspace", placeholder="Ask anything about your current session...", label_visibility="collapsed")
        st.button("Request AI Input")
        st.markdown("</div>", unsafe_allow_html=True)

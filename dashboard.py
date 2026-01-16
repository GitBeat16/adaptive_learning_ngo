import streamlit as st
import time
import uuid
import requests
from datetime import datetime, timedelta
from database import cursor, conn
from streak import init_streak # Assuming streak.py handles the DB logic
from streamlit_lottie import st_lottie

SUBJECTS = ["Mathematics", "English", "Science"]
TIME_SLOTS = ["4-5 PM", "5-6 PM", "6-7 PM"]

# -----------------------------------------------------
# UI & ANIMATION HELPERS
# -----------------------------------------------------
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def inject_emerald_dashboard_styles():
    st.markdown("""
        <style>
        .stApp { background-color: #f0fdf4; }
        
        .profile-card {
            background: white;
            padding: 30px;
            border-radius: 24px;
            border-bottom: 6px solid #10b981;
            box-shadow: 0 12px 30px rgba(5, 150, 105, 0.08);
            margin-bottom: 25px;
            color: #064e3b;
        }

        .streak-card {
            background: linear-gradient(135deg, #065f46 0%, #064e3b 100%);
            color: white;
            padding: 25px;
            border-radius: 20px;
            text-align: center;
            box-shadow: 0 10px 20px rgba(6, 95, 70, 0.2);
        }

        div.stButton > button {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 14px !important;
            padding: 0.7rem 1.5rem !important;
            font-weight: 700 !important;
            width: 100%;
            transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
            box-shadow: 0 4px 10px rgba(16, 185, 129, 0.2) !important;
        }

        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 18px rgba(16, 185, 129, 0.3) !important;
            filter: brightness(1.05);
        }

        .pulse-box {
            background: #ecfdf5;
            border: 2px solid #10b981;
            padding: 15px;
            border-radius: 15px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
            70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
            100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
        </style>
    """, unsafe_allow_html=True)

# -----------------------------------------------------
# UPDATED STREAK UI (NO EMOJIS)
# -----------------------------------------------------
def render_custom_streak():
    # Fetch streak data from database
    cursor.execute("SELECT current_streak FROM user_streaks WHERE user_id = ?", (st.session_state.user_id,))
    res = cursor.fetchone()
    streak_val = res[0] if res else 0
    
    anim_fire = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_S691S7.json") # Emerald-style flame

    st.markdown("<div class='streak-card'>", unsafe_allow_html=True)
    col1, col2 = st.columns([0.3, 0.7])
    with col1:
        if anim_fire: st_lottie(anim_fire, height=80, key="streak_fire")
    with col2:
        st.markdown(f"<h2 style='color:white; margin:0;'>{streak_val} Day Streak</h2>", unsafe_allow_html=True)
        st.caption("Keep practicing daily to grow your momentum")
    
    # Progress towards next level/milestone
    progress = (streak_val % 7) / 7.0
    st.progress(progress if progress > 0 else 0.1)
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------
# CORE LOGIC HELPERS
# -----------------------------------------------------
def load_match_history(user_id):
    cursor.execute("""
        SELECT sr.match_id, sr.rating, au.id, au.name
        FROM session_ratings sr
        JOIN auth_users au ON au.id != sr.rater_id
        WHERE sr.rater_id = ?
        ORDER BY sr.rowid DESC
    """, (user_id,))
    return cursor.fetchall()

def send_rematch_request(to_user_id):
    cursor.execute("INSERT INTO rematch_requests (from_user, to_user, status, seen) VALUES (?, ?, 'pending', 0)", 
                   (st.session_state.user_id, to_user_id))
    conn.commit()

def load_incoming_requests(user_id):
    cursor.execute("""
        SELECT rr.id, au.name, au.id, rr.seen
        FROM rematch_requests rr
        JOIN auth_users au ON au.id = rr.from_user
        WHERE rr.to_user = ? AND rr.status = 'pending'
        ORDER BY rr.id DESC
    """, (user_id,))
    return cursor.fetchall()

def accept_request(req_id, from_user_id):
    new_match_id = f"rematch_{uuid.uuid4().hex[:8]}"
    cursor.execute("UPDATE rematch_requests SET status='accepted' WHERE id=?", (req_id,))
    cursor.execute("UPDATE profiles SET status='matched', match_id=?, accepted=1 WHERE user_id IN (?, ?)", 
                   (new_match_id, st.session_state.user_id, from_user_id))
    conn.commit()

# =====================================================
# DASHBOARD PAGE
# =====================================================
def dashboard_page():
    inject_emerald_dashboard_styles()
    init_streak()

    # Load Animations
    anim_welcome = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_m6cuL6.json")
    anim_empty = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_dmw3t0vg.json")

    # 1. Active Session Pulse
    cursor.execute("SELECT status, match_id FROM profiles WHERE user_id=?", (st.session_state.user_id,))
    current_status = cursor.fetchone()

    if current_status and current_status[0] == 'matched':
        st.markdown("""
            <div class='pulse-box'>
                <h4 style='color:#065f46; margin:0;'>Active Match Detected</h4>
                <p style='color:#065f46; font-size:0.9rem;'>Your partner is waiting in the Discovery Room.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Join Partner Now", key="join_pulse"):
            st.session_state.page = "Matchmaking"
            st.rerun()
        st.write("")

    # 2. Welcome Header
    col_w1, col_w2 = st.columns([0.7, 0.3])
    with col_w1:
        st.markdown(f"<h1 style='color:#064e3b; margin-bottom:0;'>Welcome, {st.session_state.user_name}</h1>", unsafe_allow_html=True)
        st.caption("Emerald Adaptive Learning Hub | User Dashboard")
    with col_w2:
        if anim_welcome: st_lottie(anim_welcome, height=100, key="welcome_anim")

    st.divider()

    # 3. Streak Section (New UI)
    render_custom_streak()
    st.write("")

    # 4. Profile Section
    cursor.execute("SELECT role, grade, time, strong_subjects, weak_subjects, teaches FROM profiles WHERE user_id=?", (st.session_state.user_id,))
    profile = cursor.fetchone()
    edit_mode = st.session_state.get("edit_profile", False)

    if not profile or edit_mode:
        st.markdown("<div class='profile-card'>", unsafe_allow_html=True)
        with st.form("profile_form"):
            role = st.selectbox("Current Role", ["Student", "Teacher"])
            grade = st.selectbox("Grade", [f"Grade {i}" for i in range(1, 11)])
            time_slot = st.selectbox("Preferred Time", TIME_SLOTS)
            if role == "Student":
                strong = st.multiselect("Strong Subjects", SUBJECTS)
                weak = st.multiselect("Weak Subjects", SUBJECTS)
                teaches = []
            else:
                teaches = st.multiselect("Teaching Subjects", SUBJECTS)
                strong, weak = [], []
            
            if st.form_submit_button("Save Node Profile"):
                cursor.execute("""
                    INSERT OR REPLACE INTO profiles (user_id, role, grade, time, strong_subjects, weak_subjects, teaches, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'waiting')
                """, (st.session_state.user_id, role, grade, time_slot, ",".join(strong), ",".join(weak), ",".join(teaches)))
                conn.commit()
                st.session_state.edit_profile = False
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        role, grade, time_slot, strong, weak, teaches = profile
        st.markdown("<div class='profile-card'>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Node Role", role)
        c2.metric("Class Level", grade)
        c3.metric("Availability", time_slot)
        if st.button("Update Profile"):
            st.session_state.edit_profile = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # 5. History & Rematch (Replacement for "Coming Soon")
    st.markdown("### Learning Network Activity")
    col_h1, col_h2 = st.columns(2)

    with col_h1:
        st.markdown("**Session History**")
        history = load_match_history(st.session_state.user_id)
        if not history:
            st.caption("No sessions found in history.")
            if anim_empty: st_lottie(anim_empty, height=120, key="empty_hist")
        else:
            for mid, rat, pid, pname in history:
                with st.expander(f"Partner: {pname} | Score: {rat}"):
                    if st.button("Request Rematch", key=f"rem_{mid}"):
                        send_rematch_request(pid)
                        st.success("Request Broadcasted")

    with col_h2:
        st.markdown("**Incoming Rematches**")
        reqs = load_incoming_requests(st.session_state.user_id)
        if not reqs:
            st.caption("Scanning for requests...")
        else:
            for rid, sname, sid, seen in reqs:
                st.info(f"Connection request from {sname}")
                if st.button("Accept Link", key=f"acc_{rid}"):
                    accept_request(rid, sid)
                    st.session_state.page = "Matchmaking"
                    st.rerun()

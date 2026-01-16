import streamlit as st
import requests
from datetime import date
from database import cursor, conn
from streamlit_lottie import st_lottie

# -----------------------------------------------------
# ANIMATION & THEME HELPERS
# -----------------------------------------------------
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def inject_emerald_streak_styles():
    st.markdown("""
        <style>
        /* Smooth Fade-in Animation for the whole container */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .streak-container {
            background: #ffffff;
            padding: 35px;
            border-radius: 28px;
            border: 2px solid #059669; /* Darker border for definition */
            box-shadow: 0 25px 50px -12px rgba(6, 78, 59, 0.15);
            text-align: center;
            margin-bottom: 25px;
            animation: fadeIn 0.8s ease-out;
        }
        
        /* High Contrast Streak Number */
        .streak-number {
            font-size: 5rem;
            font-weight: 900;
            color: #064e3b; /* Deepest Forest Green for maximum visibility */
            line-height: 1;
            margin: 5px 0;
            text-shadow: 0px 4px 10px rgba(16, 185, 129, 0.2);
        }
        
        /* Momentum Text - Fixed Visibility */
        .streak-label {
            color: #111827; /* Near black/Dark Gray for peak readability */
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            font-size: 1.1rem;
            margin-bottom: 2px;
        }

        .level-name {
            color: #059669; /* Pure Emerald */
            font-weight: 700;
            font-size: 1.3rem;
            background: #f0fdf4;
            display: inline-block;
            padding: 4px 15px;
            border-radius: 50px;
            margin-bottom: 15px;
        }
        
        /* Progress Bar - Emerald Gradient */
        .stProgress > div > div > div > div {
            background-color: #10b981 !important;
            background-image: linear-gradient(90deg, #10b981 0%, #059669 100%) !important;
        }

        .streak-caption {
            color: #374151; /* Darker caption text */
            font-weight: 600;
            font-size: 0.95rem;
            margin-top: 8px;
        }
        </style>
    """, unsafe_allow_html=True)

# -----------------------------------------------------
# CORE LOGIC
# -----------------------------------------------------
def init_streak():
    if "streak" not in st.session_state:
        st.session_state.streak = 0
    if "last_active" not in st.session_state:
        st.session_state.last_active = None

    user_id = st.session_state.get("user_id")
    if not user_id:
        return

    cursor.execute(
        "SELECT streak, last_active FROM user_streaks WHERE user_id=?",
        (user_id,)
    )
    row = cursor.fetchone()

    if row:
        st.session_state.streak = row[0]
        st.session_state.last_active = (
            date.fromisoformat(row[1]) if row[1] else None
        )
    else:
        cursor.execute(
            "INSERT INTO user_streaks (user_id, streak, last_active) VALUES (?, 0, NULL)",
            (user_id,)
        )
        conn.commit()

def update_streak():
    init_streak()
    today = date.today()
    last = st.session_state.last_active

    if last != today:
        if last is None:
            st.session_state.streak = 1
        else:
            delta = (today - last).days
            st.session_state.streak = (
                st.session_state.streak + 1 if delta == 1 else 1
            )

        st.session_state.last_active = today
        cursor.execute("""
            UPDATE user_streaks SET streak=?, last_active=? WHERE user_id=?
        """, (st.session_state.streak, today.isoformat(), st.session_state.user_id))
        conn.commit()
        return True
    return False

# -----------------------------------------------------
# UI RENDERING (ENHANCED CONTRAST)
# -----------------------------------------------------
STREAK_LEVELS = [
    (0, "Phase: Seedling", "https://assets3.lottiefiles.com/packages/lf20_7msh8sn0.json"), 
    (3, "Phase: Growing", "https://assets1.lottiefiles.com/private_files/lf30_8ez6ny.json"), 
    (7, "Phase: Established", "https://assets1.lottiefiles.com/packages/lf20_08m9ayre.json"), 
    (14, "Phase: Legend", "https://lottie.host/81a9673d-907a-426c-850d-851f5056804d/5vK5oXpL5I.json") 
]

def render_streak_ui():
    init_streak()
    inject_emerald_streak_styles()
    
    streak = st.session_state.streak
    
    # Selection logic
    current_level_name = "Phase: Seedling"
    active_anim_url = STREAK_LEVELS[0][2]
    
    for days, name, url in STREAK_LEVELS:
        if streak >= days:
            current_level_name = name
            active_anim_url = url

    anim_data = load_lottieurl(active_anim_url)

    # Main Container
    st.markdown("<div class='streak-container'>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([0.45, 0.55])
    
    with col1:
        if anim_data:
            st_lottie(anim_data, height=240, key="streak_anim_high_vis", speed=1)
            
    with col2:
        # Fixed Visibility Text
        st.markdown(f"<div class='streak-label'>{streak} Day Momentum</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='streak-number'>{streak}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='level-name'>{current_level_name}</div>", unsafe_allow_html=True)
        
        # Progress Calculation
        weekly_step = streak % 7
        progress_val = 1.0 if (streak > 0 and weekly_step == 0) else (weekly_step / 7.0)
            
        st.progress(max(progress_val, 0.05))
        st.markdown(f"<div class='streak-caption'>Network Synchronization: {int(progress_val*100)}%</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Status Notification
    if streak == 0:
        st.info("Your streak is inactive. Complete a practice session to begin.")
    else:
        st.success(f"System Active. You have maintained a {streak} day connection.")

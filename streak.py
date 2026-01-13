import streamlit as st
from datetime import date
from database import cursor, conn

# ---------- INIT ----------
def init_streak():
    if "streak" not in st.session_state:
        st.session_state.streak = 0
    if "last_active" not in st.session_state:
        st.session_state.last_active = None
    if "unlocks_seen" not in st.session_state:
        st.session_state.unlocks_seen = set()

    user_id = st.session_state.get("user_id")
    if not user_id:
        return

    # Load from DB (once per session)
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

# ---------- UPDATE ----------
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
            UPDATE user_streaks
            SET streak=?, last_active=?
            WHERE user_id=?
        """, (
            st.session_state.streak,
            today.isoformat(),
            st.session_state.user_id
        ))
        conn.commit()
        return True

    return False

# ---------- UI ----------
STREAK_LEVELS = [
    (1, "Beginner 🌱"),
    (3, "Consistent Learner 🌿"),
    (6, "Study Champ 🌳"),
    (11, "Knowledge Warrior 🌲"),
    (21, "Legend 🏆")
]

EMOTIONAL_MESSAGES = {
    0: "Your learning journey is waiting 🌱",
    1: "Great start! Keep going 💧",
    3: "Consistency beats talent 🔥",
    7: "One week strong 💪",
    14: "Discipline is power 🌳",
}

def get_streak_level(streak):
    level = "Beginner 🌱"
    for days, name in STREAK_LEVELS:
        if streak >= days:
            level = name
    return level

def get_message(streak):
    msg = EMOTIONAL_MESSAGES[0]
    for k in sorted(EMOTIONAL_MESSAGES):
        if streak >= k:
            msg = EMOTIONAL_MESSAGES[k]
    return msg

def render_streak_ui():
    init_streak()
    streak = st.session_state.streak

    st.subheader("🌱 Your Learning Plant")
    st.markdown(f"### 🔥 {streak}-Day Streak")
    st.markdown(f"**🏅 Level:** {get_streak_level(streak)}")
    st.info(get_message(streak))

    progress = min(streak % 7 or 7, 7)
    st.progress(progress / 7)
    st.caption(f"Weekly Progress: {progress}/7 days")

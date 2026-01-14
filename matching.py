import streamlit as st
import os
from database import cursor, conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads/sessions"
MATCH_THRESHOLD = 30

# =========================================================
# LOAD USERS
# =========================================================
def load_profiles():
    cursor.execute("""
        SELECT a.id, a.name, p.role, p.grade, p.time,
               p.strong_subjects, p.weak_subjects, p.teaches
        FROM profiles p
        JOIN auth_users a ON a.id = p.user_id
        WHERE p.status = 'waiting'
    """)
    rows = cursor.fetchall()

    users = []
    for r in rows:
        users.append({
            "user_id": r[0],
            "name": r[1],
            "role": r[2],
            "grade": r[3],
            "time": r[4],
            "strong": (r[7] or r[5] or "").split(","),
            "weak": (r[6] or "").split(",")
        })
    return users

# =========================================================
# MATCH LOGIC
# =========================================================
def score(u1, u2):
    s = 0
    s += len(set(u1["weak"]) & set(u2["strong"])) * 25
    s += len(set(u2["weak"]) & set(u1["strong"])) * 25
    if u1["grade"] == u2["grade"]:
        s += 10
    if u1["time"] == u2["time"]:
        s += 10
    return s

def find_best(current, users):
    best, best_s = None, 0
    for u in users:
        if u["user_id"] == current["user_id"]:
            continue
        sc = score(current, u)
        if sc > best_s:
            best, best_s = u, sc
    return (best, best_s) if best_s >= MATCH_THRESHOLD else (None, 0)

# =========================================================
# CHAT + FILE HELPERS
# =========================================================
def load_msgs(mid):
    cursor.execute(
        "SELECT sender, message FROM messages WHERE match_id=? ORDER BY id",
        (mid,)
    )
    return cursor.fetchall()

def send_msg(mid, sender, message):
    cursor.execute(
        "INSERT INTO messages (match_id, sender, message) VALUES (?, ?, ?)",
        (mid, sender, message)
    )
    conn.commit()

def save_file(mid, uploader, file):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    path = f"{UPLOAD_DIR}/{mid}_{file.name}"
    with open(path, "wb") as out:
        out.write(file.getbuffer())

    cursor.execute("""
        INSERT INTO session_files (match_id, uploader, filename, filepath)
        VALUES (?, ?, ?, ?)
    """, (mid, uploader, file.name, path))
    conn.commit()

def load_files(mid):
    cursor.execute("""
        SELECT uploader, filename, filepath
        FROM session_files
        WHERE match_id=?
        ORDER BY uploaded_at
    """, (mid,))
    return cursor.fetchall()

# =========================================================
# END SESSION
# =========================================================
def end_session(match_id):
    cursor.execute("""
        UPDATE profiles
        SET status='waiting', match_id=NULL
        WHERE match_id=?
    """, (match_id,))
    conn.commit()

# =========================================================
# ⭐ RATING UI
# =========================================================
def show_rating_ui(match_id):

    cursor.execute("""
        SELECT 1 FROM session_ratings
        WHERE match_id=? AND rater_id=?
    """, (match_id, st.session_state.user_id))

    if cursor.fetchone():
        st.info("You already rated this session.")
        return

    st.markdown("### ⭐ Rate Your Session")

    if "rating" not in st.session_state:
        st.session_state.rating = 0

    cols = st.columns(5)
    for i in range(5):
        if cols[i].button("⭐" if i < st.session_state.rating else "☆", key=f"star_{i}"):
            st.session_state.rating = i + 1

    if st.button("Submit Rating", use_container_width=True):
        if st.session_state.rating == 0:
            st.warning("Please select a rating.")
            return

        cursor.execute("""
            INSERT INTO session_ratings
            (match_id, rater_id, rater_name, rating)
            VALUES (?, ?, ?, ?)
        """, (
            match_id,
            st.session_state.user_id,
            st.session_state.user_name,
            st.session_state.rating
        ))
        conn.commit()

        st.success("Thank you for your feedback! 🎉")
        st.session_state.rating_submitted = True

# =========================================================
# PAGE
# =========================================================
def matchmaking_page():

    for k in ["celebrated", "session_ended", "rating_submitted"]:
        if k not in st.session_state:
            st.session_state[k] = False

    st.markdown("""
    <div style="padding:1.5rem;border-radius:16px;
    background:linear-gradient(135deg,#4f46e5,#6366f1);color:white;">
        <h2>Peer Learning Session</h2>
        <p>Match, learn, and collaborate</p>
    </div>
    """, unsafe_allow_html=True)

    cursor.execute("""
        SELECT role, grade, time, strong_subjects, weak_subjects, teaches, match_id
        FROM profiles WHERE user_id=?
    """, (st.session_state.user_id,))
    row = cursor.fetchone()
    if not row:
        st.warning("Complete your profile first.")
        return

    role, grade, time_slot, strong, weak, teaches, match_id = row

    user = {
        "user_id": st.session_state.user_id,
        "name": st.session_state.user_name,
        "role": role,
        "grade": grade,
        "time": time_slot,
        "strong": (teaches or strong or "").split(","),
        "weak": (weak or "").split(",")
    }

    # 🤖 AI ASSISTANT
    st.markdown("### 🤖 AI Study Assistant")
    with st.form("ai"):
        q = st.text_input("Ask anything")
        if st.form_submit_button("Ask") and q:
            st.success(ask_ai(q))

    st.divider()

    # MATCHING
    if not match_id:
        if st.button("Find Best Match", use_container_width=True):
            m, s = find_best(user, load_profiles())
            if m:
                st.session_state.match = m
                st.session_state.score = s

        if "match" in st.session_state:
            m = st.session_state.match
            st.markdown(f"### Suggested Match: **{m['name']}**")
            if st.button("Confirm Match", use_container_width=True):
                mid = f"{user['user_id']}-{m['user_id']}"
                cursor.execute("""
                    UPDATE profiles SET status='matched', match_id=?
                    WHERE user_id IN (?,?)
                """, (mid, user["user_id"], m["user_id"]))
                conn.commit()
                st.session_state.celebrated = False
                st.rerun()
        return

    # 🎉 CONFETTI + 🔊 SOUND
    if not st.session_state.celebrated:
        st.success("🎉 You're matched! Welcome to your live session.")

        st.components.v1.html("""
        <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
        <script>
          confetti({ particleCount: 200, spread: 120, origin: { y: 0.6 }});
        </script>
        """, height=0)

        st.audio(
            "https://actions.google.com/sounds/v1/ui/confirmation.ogg",
            autoplay=True
        )

        st.session_state.celebrated = True

    # 🔴 END SESSION BUTTON (CENTERED)
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        if not st.session_state.session_ended:
            if st.button("End Session", use_container_width=True):
                end_session(match_id)
                st.session_state.session_ended = True

    st.divider()

    # LIVE CHAT
    st.markdown("### Live Learning Room")
    for s, m in load_msgs(match_id):
        st.markdown(f"**{s}:** {m}")

    with st.form("chat"):
        msg = st.text_input("Message")
        if st.form_submit_button("Send") and msg:
            send_msg(match_id, user["name"], msg)
            st.rerun()

    # FILES
    st.divider()
    st.markdown("### Shared Resources")
    with st.form("files"):
        f = st.file_uploader("Upload")
        if st.form_submit_button("Upload") and f:
            save_file(match_id, user["name"], f)
            st.rerun()

    for u, n, p in load_files(match_id):
        with open(p, "rb") as file:
            st.download_button(n, file, use_container_width=True)

    # ⭐ RATING AFTER END
    if st.session_state.session_ended and not st.session_state.rating_submitted:
        show_rating_ui(match_id)

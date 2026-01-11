import streamlit as st
from groq import Groq
from supabase import create_client, Client
import time

# =========================================================
# CONFIGURATION
# =========================================================
st.set_page_config(page_title="Sahay: Llama 3 Powered", layout="wide")

# 1. SETUP SUPABASE
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"❌ Supabase Error: {e}")
    st.stop()

# 2. SETUP GROQ AI (The New Fast AI)
ai_client = None
if "GROQ_API_KEY" in st.secrets:
    try:
        ai_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    except Exception as e:
        st.warning(f"Groq Config Error: {e}")
else:
    st.warning("⚠️ GROQ_API_KEY missing in Secrets. AI will not work.")

# =========================================================
# 🧠 ROBUST MATCHING ALGORITHM
# =========================================================
def calculate_match_score(me, candidate):
    score = 0
    
    # Safe String Handling
    my_lang = set(x.strip() for x in (me.get('languages') or "").split(',') if x.strip())
    their_lang = set(x.strip() for x in (candidate.get('languages') or "").split(',') if x.strip())
    
    # 1. Language Barrier (Critical)
    if not my_lang.intersection(their_lang):
        return 0 # Fail
    score += 20 

    # 2. Subject Match
    my_subs = set(x.strip() for x in (me.get('subjects') or "").split(',') if x.strip())
    their_subs = set(x.strip() for x in (candidate.get('subjects') or "").split(',') if x.strip())
    
    if my_subs.intersection(their_subs):
        score += 40
    else:
        return 0 # Fail

    # 3. Grade Logic
    try:
        my_g = int(me['grade'].split(" ")[1])
        their_g = int(candidate['grade'].split(" ")[1])
        diff = their_g - my_g

        if me['role'] == "Student":
            if diff > 0: score += 30
            elif diff == 0: score += 15
        else:
            if diff < 0: score += 30
    except: pass 

    return score

def find_best_match(my_profile):
    opposite = "Teacher" if my_profile['role'] == "Student" else "Student"
    
    response = supabase.table("profiles").select("*")\
        .eq("role", opposite)\
        .eq("time_slot", my_profile['time_slot'])\
        .eq("status", "waiting")\
        .execute()
    
    candidates = response.data
    if not candidates: return None

    best = None
    high_score = 0
    
    for p in candidates:
        s = calculate_match_score(my_profile, p)
        if s > high_score:
            high_score = s
            best = p

    return best

# =========================================================
# DATABASE HELPERS
# =========================================================
def save_profile(data):
    data['subjects'] = ", ".join(data['subjects'])
    data['languages'] = ",".join(data['languages'])
    try:
        supabase.table("profiles").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"DB Error: {e}")
        return False

def create_match_record(p1, p2):
    names = sorted([p1, p2])
    m_id = f"{names[0]}-{names[1]}"
    try:
        # Check if exists
        check = supabase.table("matches").select("*").eq("match_id", m_id).execute()
        if not check.data:
            supabase.table("matches").insert({
                "match_id": m_id, "mentor": p1, "mentee": p2
            }).execute()
            # Update status
            supabase.table("profiles").update({"status": "matched"}).eq("name", p1).execute()
            supabase.table("profiles").update({"status": "matched"}).eq("name", p2).execute()
    except: pass
    return m_id

# =========================================================
# APP UI
# =========================================================
if "stage" not in st.session_state: st.session_state.stage = 1
if "user_name" not in st.session_state: st.session_state.user_name = ""

st.title("Sahay: Peer Learning (Powered by Llama 3 🦙)")

# STAGE 1: PROFILE
if st.session_state.stage == 1:
    st.header("Step 1: Your Profile")
    col1, col2 = st.columns(2)
    with col1:
        role = st.radio("I am a:", ["Student", "Teacher"])
        name = st.text_input("Full Name")
        languages = st.multiselect("Languages", ["English", "Hindi", "Marathi", "Tamil"])
    with col2:
        grade = st.selectbox("Grade", [f"Grade {i}" for i in range(5, 13)])
        time_slot = st.selectbox("Time Slot", ["4-5 PM", "5-6 PM"])
        
    subjects = st.multiselect("Subjects", ["Math", "Science", "English", "History"])
    topics = st.text_input("Specific Topic (e.g. Algebra)")

    if st.button("Find Match", type="primary"):
        if name and subjects and languages:
            profile = {
                "role": role, "name": name, "grade": grade, 
                "time_slot": time_slot, "subjects": subjects,
                "languages": languages, "specific_topics": topics, "status": "waiting"
            }
            if save_profile(profile):
                st.session_state.profile = profile
                st.session_state.user_name = name
                st.session_state.stage = 2
                st.rerun()
        else:
            st.warning("Fill all details!")

# STAGE 2: SEARCH
elif st.session_state.stage == 2:
    st.header("Step 2: Analysis")
    if st.button("🔄 Analyze & Match"):
        match = find_best_match(st.session_state.profile)
        if match:
            st.success(f"Match Found: **{match['name']}**")
            m_id = create_match_record(st.session_state.user_name, match['name'])
            st.session_state.match_id = m_id
            st.session_state.partner_name = match['name']
            time.sleep(1)
            st.session_state.stage = 3
            st.rerun()
        else:
            st.warning("No match found yet.")

# STAGE 3: CHAT
elif st.session_state.stage == 3:
    st.header(f"Session: {st.session_state.user_name} & {st.session_state.partner_name}")
    
    col_chat, col_tools = st.columns([2, 1])
    
    with col_chat:
        try:
            msgs = supabase.table("messages").select("*").eq("match_id", st.session_state.match_id).order("created_at").execute().data
        except: msgs = []

        with st.container(height=400):
            for m in msgs:
                is_me = m['sender'] == st.session_state.user_name
                with st.chat_message("user" if is_me else "assistant"):
                    st.write(f"**{m['sender']}**: {m['message']}")

        if prompt := st.chat_input("Message..."):
            supabase.table("messages").insert({
                "match_id": st.session_state.match_id, "sender": st.session_state.user_name, "message": prompt
            }).execute()
            st.rerun()
            
    with col_tools:
        if st.button("Refresh Chat"): st.rerun()
        
        # --- GROQ AI HINT BUTTON ---
        if st.button("🤖 AI Hint (Llama 3)"):
            if ai_client:
                try:
                    # 1. Get Context
                    context_msgs = [m['message'] for m in msgs[-3:] if m['message']]
                    context = " ".join(context_msgs) if context_msgs else "No context."
                    
                    # 2. Call Groq API
                    completion = ai_client.chat.completions.create(
                        model="llama3-8b-8192", # Fast & Free
                        messages=[
                            {"role": "system", "content": "You are a helpful tutor. Give a short, 1-sentence hint."},
                            {"role": "user", "content": f"Context: {context}"}
                        ],
                        temperature=0.7,
                        max_tokens=100
                    )
                    
                    ai_reply = completion.choices[0].message.content
                    
                    # 3. Save to DB
                    supabase.table("messages").insert({
                        "match_id": st.session_state.match_id, 
                        "sender": "AI Bot", 
                        "message": f"🤖 {ai_reply}"
                    }).execute()
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"AI Error: {e}")
            else:
                st.error("AI Key Missing")

        if st.button("End Session"):
            st.session_state.stage = 1
            st.rerun()

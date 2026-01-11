import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import time
from datetime import datetime

# =========================================================
# CONFIGURATION
# =========================================================
st.set_page_config(page_title="Sahay Live + Files", layout="wide")

# =========================================================
# SUPABASE CONNECTION
# =========================================================
# Initialize connection safely
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase: Client = init_supabase()
except:
    st.error("⚠️ Supabase Credentials Missing in Secrets!")
    st.stop()

# =========================================================
# DATABASE FUNCTIONS
# =========================================================

def save_profile(data):
    """Saves user profile to Supabase"""
    # Convert list to string for DB
    data['subjects'] = ", ".join(data['subjects'])
    data['status'] = 'waiting'
    try:
        supabase.table("profiles").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error saving profile: {e}")
        return False

def find_match(role, time_slot, grade):
    """Finds a waiting peer with opposite role"""
    opposite = "Teacher" if role == "Student" else "Student"
    
    # Query Supabase: Find opposite role, same time, status waiting
    response = supabase.table("profiles").select("*")\
        .eq("role", opposite)\
        .eq("time_slot", time_slot)\
        .eq("status", "waiting")\
        .execute()
    
    candidates = response.data
    if candidates:
        return candidates[0] # Return first match
    return None

def create_match_record(mentor, mentee):
    match_id = f"{mentor}-{mentee}"
    # Check if exists first to avoid duplicate errors
    existing = supabase.table("matches").select("*").eq("match_id", match_id).execute()
    
    if not existing.data:
        supabase.table("matches").insert({
            "match_id": match_id,
            "mentor": mentor,
            "mentee": mentee
        }).execute()
        
        # Update profiles to 'matched' so they stop appearing in search
        supabase.table("profiles").update({"status": "matched"}).eq("name", mentor).execute()
        supabase.table("profiles").update({"status": "matched"}).eq("name", mentee).execute()
        
    return match_id

def send_message(match_id, sender, text=None, file_url=None, file_type=None):
    data = {
        "match_id": match_id,
        "sender": sender,
        "message": text if text else "",
        "file_url": file_url,
        "file_type": file_type
    }
    supabase.table("messages").insert(data).execute()

def get_messages(match_id):
    # Get messages ordered by time
    response = supabase.table("messages").select("*")\
        .eq("match_id", match_id)\
        .order("created_at", desc=False)\
        .execute()
    return response.data

def upload_file(file_obj, match_id):
    """Uploads file to Supabase Storage and returns URL"""
    try:
        # Create unique filename: match_id/timestamp_filename
        file_path = f"{match_id}/{int(time.time())}_{file_obj.name}"
        bucket = "chat-files"
        
        # Upload bytes
        supabase.storage.from_(bucket).upload(
            file_path, 
            file_obj.getvalue(),
            {"content-type": file_obj.type}
        )
        
        # Get Public URL
        public_url = supabase.storage.from_(bucket).get_public_url(file_path)
        return public_url
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None

# =========================================================
# APP UI
# =========================================================
if "stage" not in st.session_state: st.session_state.stage = 1
if "user_name" not in st.session_state: st.session_state.user_name = ""

st.title("Sahay: Live Peer Learning 🎓")

# ---------------------------------------------------------
# STAGE 1: LOGIN
# ---------------------------------------------------------
if st.session_state.stage == 1:
    st.header("Step 1: Join Session")
    col1, col2 = st.columns(2)
    with col1:
        role = st.radio("I am a:", ["Student", "Teacher"])
        name = st.text_input("Name")
    with col2:
        grade = st.selectbox("Grade", ["Grade 8", "Grade 9", "Grade 10"])
        time_slot = st.selectbox("Time Slot", ["4-5 PM", "5-6 PM"])
    
    subjects = st.multiselect("Subjects", ["Math", "Science", "English"])

    if st.button("Go Live", type="primary"):
        if name:
            profile = {
                "role": role, "name": name, "grade": grade, 
                "time_slot": time_slot, "subjects": subjects
            }
            if save_profile(profile):
                st.session_state.profile = profile
                st.session_state.user_name = name
                st.session_state.stage = 2
                st.rerun()

# ---------------------------------------------------------
# STAGE 2: MATCHING
# ---------------------------------------------------------
elif st.session_state.stage == 2:
    st.header("Step 2: Finding Partner...")
    st.info(f"Searching for peers in {st.session_state.profile['time_slot']}...")
    
    if st.button("🔄 Check Now"):
        partner = find_match(
            st.session_state.profile['role'],
            st.session_state.profile['time_slot'],
            st.session_state.profile['grade']
        )
        
        if partner:
            st.success(f"Match Found! Connected with {partner['name']}")
            
            # Determine Match ID
            p1 = st.session_state.user_name
            p2 = partner['name']
            
            # Identify mentor/mentee for ID generation
            if st.session_state.profile['role'] == "Teacher":
                m_id = create_match_record(p1, p2)
            else:
                m_id = create_match_record(p2, p1)
            
            st.session_state.match_id = m_id
            st.session_state.partner_name = partner['name']
            time.sleep(1)
            st.session_state.stage = 3
            st.rerun()
        else:
            st.warning("No partner found yet. Please wait...")

# ---------------------------------------------------------
# STAGE 3: CHAT & FILES
# ---------------------------------------------------------
elif st.session_state.stage == 3:
    st.header(f"Chat: {st.session_state.user_name} & {st.session_state.partner_name}")
    
    # AI Setup
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

    col_chat, col_tools = st.columns([2, 1])

    with col_chat:
        st.subheader("Discussion")
        
        # Poll for new messages
        msgs = get_messages(st.session_state.match_id)
        
        container = st.container(height=400)
        with container:
            if msgs:
                for m in msgs:
                    is_me = m['sender'] == st.session_state.user_name
                    with st.chat_message("user" if is_me else "assistant"):
                        # Show Text
                        if m['message']:
                            st.write(f"**{m['sender']}:** {m['message']}")
                        
                        # Show File
                        if m['file_url']:
                            if "image" in m['file_type']:
                                st.image(m['file_url'], caption="Shared Image")
                            else:
                                st.markdown(f"📎 [Download File]({m['file_url']})")
            else:
                st.info("Start the conversation!")

        # Message Input
        with st.form("chat"):
            txt = st.text_input("Message...")
            sent = st.form_submit_button("Send")
            if sent and txt:
                send_message(st.session_state.match_id, st.session_state.user_name, text=txt)
                st.rerun()
        
        if st.button("🔄 Refresh Chat"):
            st.rerun()

    with col_tools:
        st.subheader("Share Files")
        
        # File Uploader
        uploaded_file = st.file_uploader("Upload Image/PDF", key="up")
        if uploaded_file and st.button("Upload"):
            with st.spinner("Uploading..."):
                url = upload_file(uploaded_file, st.session_state.match_id)
                if url:
                    send_message(
                        st.session_state.match_id, 
                        st.session_state.user_name, 
                        file_url=url, 
                        file_type=uploaded_file.type
                    )
                    st.success("File sent!")
                    st.rerun()

        st.divider()
        st.subheader("AI Helper")
        if st.button("🤖 Ask AI Hint"):
            if msgs:
                last_txt = next((m['message'] for m in reversed(msgs) if m['message']), "Hello")
                model = genai.GenerativeModel("gemini-1.5-flash")
                resp = model.generate_content(f"Student asked: '{last_txt}'. Give a short hint.")
                send_message(st.session_state.match_id, "AI Bot", text=f"🤖 {resp.text}")
                st.rerun()

        if st.button("End Session"):
            st.session_state.stage = 1
            st.rerun()

import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai
import io
from gtts import gTTS
import time
from datetime import datetime, timedelta
import requests
from streamlit_lottie import st_lottie
from streamlit_mic_recorder import speech_to_text
import json
import os
import random
from typing import List, Optional, Generator, Union, Any

# --- 1. Configuration & Constants ---
PAGE_TITLE = "Study With Me"
PAGE_ICON = "🎓"
LAYOUT = "wide"

THEMES = {
    "☀️ Light": {
        "bg": "#f8f9fa",
        "text": "#212529",
        "card": "#ffffff",
        "sidebar": "#ffffff",
        "accent": "#1a73e8",
        "border": "#e0e0e0",
        "secondary_bg": "#f1f3f4"
    },
    "🌑 Dark": {
        "bg": "#0e1117",
        "text": "#fafafa",
        "card": "#262730",
        "sidebar": "#262730",
        "accent": "#8ab4f8",
        "border": "#3d3d3d",
        "secondary_bg": "#1e1e1e"
    },
    "☕ Coffee": {
        "bg": "#fdf6e3",
        "text": "#586e75",
        "card": "#eee8d5",
        "sidebar": "#eee8d5",
        "accent": "#b58900",
        "border": "#d3cbb8",
        "secondary_bg": "#fdf6e3"
    }
}

# --- 2. Setup & Initialization ---
def setup_page():
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout=LAYOUT)

def init_session_state():
    defaults = {
        "current_theme": "☀️ Light",
        "messages": [],
        "pdf_images": None,
        "text_content": None,
        "content_type": None,
        "study_end_time": None,
        "student_name": "Champion",
        "quiz_data": None,
        "active_api_key_index": 0
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- 3. Style & UI/UX ---
def apply_theme(theme_name: str):
    t = THEMES[theme_name]
    custom_css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&family=Inter:wght@400;600&display=swap');
        
        :root {{
            --primary-color: {t['accent']};
            --bg-color: {t['bg']};
            --text-color: {t['text']};
            --card-bg: {t['card']};
            --border-color: {t['border']};
        }}
        
        html, body, [class*="st-"] {{ 
            font-family: 'Cairo', 'Inter', sans-serif !important; 
        }}
        
        .stApp {{ background-color: {t['bg']}; color: {t['text']}; }}
        
        /* Sidebar */
        section[data-testid="stSidebar"] {{ 
            background-color: {t['sidebar']}; 
            border-right: 1px solid {t['border']}; 
        }}

        /* Buttons */
        .stButton > button {{
            background: linear-gradient(135deg, {t['accent']}, {t['accent']}dd);
            color: {t['bg'] if theme_name != '🌑 Dark' else '#fff'} !important; 
            border: none; 
            border-radius: 12px;
            padding: 0.6rem 1.2rem;
            font-weight: 600;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stButton > button:hover {{ 
            transform: translateY(-2px); 
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
            filter: brightness(110%);
        }}
        .stButton > button:active {{ transform: translateY(0); }}

        /* Cards & Containers */
        .css-card, [data-testid="stExpander"], div.stTabs [data-baseweb="tab-list"] {{
            background-color: {t['card']};
            border: 1px solid {t['border']};
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        /* Headers */
        h1, h2, h3, h4 {{ 
            color: {t['accent']} !important; 
            font-weight: 700; 
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab"] {{
            height: 3rem;
            border-radius: 8px;
            font-weight: 600;
            color: {t['text']};
            margin: 0 4px;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {t['accent']}20 !important;
            color: {t['accent']} !important;
        }}

        /* Chat Messages */
        [data-testid="stChatMessage"] {{
            background-color: {t['card']};
            border: 1px solid {t['border']};
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 0.8rem;
        }}
        [data-testid="stChatMessage"].st-emotion-cache-12fmjuu {{ /* User message specific if needed */ }}

        /* Footer */
        .footer-container {{
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background-color: {t['card']};
            border-top: 1px solid {t['border']};
            padding: 15px 0;
            text-align: center;
            z-index: 999;
            box-shadow: 0 -4px 10px rgba(0,0,0,0.05);
        }}
        .footer-content {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            color: {t['text']};
        }}
        .social-link {{
            text-decoration: none;
            color: {t['accent']};
            font-weight: 600;
            padding: 5px 10px;
            border-radius: 8px;
            transition: background 0.2s;
        }}
        .social-link:hover {{
            background-color: {t['accent']}15;
            text-decoration: none;
        }}
        .main-content {{
            margin-bottom: 80px; /* Space for footer */
        }}
        
        /* Elements hiding */
        header {{ visibility: visible !important; }}
        .stDeployButton {{ display: none !important; }}
        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

# --- 4. Logic & Core Functions ---

@st.cache_resource(show_spinner=False)
def load_lottie_url(url: str):
    """Loads Lottie animation from URL with caching."""
    try:
        r = requests.get(url)
        if r.status_code != 200: return None
        return r.json()
    except: return None

@st.cache_data(show_spinner=False)
def process_pdf(file_bytes: bytes) -> Optional[List[Image.Image]]:
    """Converts PDF bytes to images using PyMuPDF."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        images = []
        # Import PIL here to ensure it's available in cached function scope if needed, 
        # though globally imported usually fine.
        for page_num in range(min(5, len(doc))):
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            images.append(img)
        return images
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        return None

@st.cache_data(show_spinner=False)
def text_to_audio_bytes(text: str) -> Optional[bytes]:
    """Converts text to audio using gTTS."""
    try:
        if not text or not text.strip(): return None
        clean = text.replace("*", "").replace("#", "").replace("-", "")
        clean = clean.replace("||FLASH||", "").replace("||SPLIT||", "")
        tts = gTTS(text=clean, lang='ar')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.getvalue()
    except: return None

def update_visitor_count():
    file_path = "counter.txt"
    if not os.path.exists(file_path):
        with open(file_path, "w") as f: f.write("0")
    
    try:
        with open(file_path, "r") as f: count = int(f.read())
    except: count = 0
    
    if "visited" not in st.session_state:
        count += 1
        with open(file_path, "w") as f: f.write(str(count))
        st.session_state.visited = True
    return count

# --- 5. AI & API Logic (with Rotation) ---

def get_api_key() -> Optional[str]:
    """Retrieves an API key, handling rotation strategies."""
    keys = []
    
    # Check for list of keys
    if "GEMINI_API_KEYS" in st.secrets:
        keys = st.secrets["GEMINI_API_KEYS"]
        if isinstance(keys, str): # Handle string representation of list if parsed incorrectly
            try: keys = json.loads(keys)
            except: keys = [keys]
            
    # Check for single key if no list or empty
    if not keys and "GEMINI_API_KEY" in st.secrets:
        keys = [st.secrets["GEMINI_API_KEY"]]
        
    if not keys: return None
    
    # Simple rotation: use mod index
    idx = st.session_state.get('active_api_key_index', 0) % len(keys)
    return keys[idx]

def rotate_api_key():
    """Increments the API key index to try the next key."""
    st.session_state.active_api_key_index = st.session_state.get('active_api_key_index', 0) + 1

def configure_genai(api_key: str):
    genai.configure(api_key=api_key)

def get_gemini_response(prompt: str, content_data: Any, is_images: bool = True, model_name: str = "models/gemini-1.5-flash") -> str:
    """Generates content using Gemini with retry logic and key rotation."""
    
    max_retries = 3
    
    for attempt in range(max_retries):
        api_key = get_api_key()
        if not api_key: return "⚠️ API Key not found. Please configure secrets."
        
        configure_genai(api_key)
        model = genai.GenerativeModel(model_name)
        
        content = [prompt] + content_data if is_images else [prompt + "\n\n" + str(content_data)]
        
        try:
            response = model.generate_content(content)
            return response.text
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Quota exceeded" in err_str:
                if attempt < max_retries - 1:
                    rotate_api_key() # Try next key immediately
                    time.sleep(1) # Small backoff
                    continue
                else:
                     return "⏳ Server busy (Quota Exceeded). Please try again later."
            else:
                 return f"An unexpected error occurred: {e}"

    return "❌ Operation failed after multiple attempts."

# --- 6. Main Application Body ---

def main():
    setup_page()
    init_session_state()
    
    # -- Theme Selection --
    # Sidebar
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
        st.title("Settings ⚙️")
        
        st.subheader("Theme")
        selected_theme = st.selectbox(
            "Choose Theme:", 
            list(THEMES.keys()), 
            index=list(THEMES.keys()).index(st.session_state.current_theme)
        )
        if selected_theme != st.session_state.current_theme:
            st.session_state.current_theme = selected_theme
            st.rerun()
            
        st.subheader("User Profile")
        st.session_state.student_name = st.text_input("Name:", st.session_state.student_name)
        
        st.divider()
        st.subheader("Study Tools")
        
        # Tools logic
        if st.button("🃏 Flashcards"):
            if st.session_state.pdf_images or st.session_state.text_content:
                st.session_state.messages.append({"role": "user", "content": "I need Flashcards."})
                st.session_state.trigger_flashcards = True 
                st.rerun()
            else: st.toast("Please upload a file first!", icon="📂")

        if st.button("📝 Quiz"):
            if st.session_state.pdf_images or st.session_state.text_content:
                st.session_state.trigger_quiz = True
                st.rerun()
            else: st.toast("Please upload a file first!", icon="📂")

        st.divider()
        st.subheader("Focus Timer")
        now = datetime.now()
        active_study = False
        
        if st.session_state.study_end_time:
            if now < st.session_state.study_end_time:
                time_left = st.session_state.study_end_time - now
                mins, secs = divmod(int(time_left.total_seconds()), 60)
                st.info(f"📚 Remaining: {mins}:{secs:02d}")
                active_study = True
                if st.button("Stop Session ⏹️"):
                    st.session_state.study_end_time = None
                    st.rerun()
            else:
                st.session_state.study_end_time = None
                st.balloons()
                st.success("Session Complete! 🎉")
                st.rerun()
                
        if not active_study:
            minutes = st.slider("Duration (min):", 5, 120, 25)
            if st.button("Start Focus 🚀"):
                st.session_state.study_end_time = now + timedelta(minutes=minutes)
                st.rerun()
                
        st.divider()
        if st.button("Clear Chat 🗑️"):
            st.session_state.messages = []
            st.session_state.pdf_images = None
            st.session_state.text_content = None
            st.session_state.content_type = None
            st.rerun()

        visitor_count = update_visitor_count()
        st.markdown(f"<p style='text-align: center; opacity: 0.7; font-size: 0.8rem;'>Visits: {visitor_count}</p>", unsafe_allow_html=True)

    # Apply CSS
    apply_theme(st.session_state.current_theme)

    # Main Content Area
    st.markdown('<div class="main-content">', unsafe_allow_html=True) # Start main content wrapper
    
    st.title("🎓 Study With Me")
    st.caption(f"Welcome back, {st.session_state.student_name}! What are we learning today?")

    # Lottie Loader
    lottie_study = load_lottie_url("https://lottie.host/5a67b4eb-d731-417c-9b8b-871a9388319f/7Q0q9q9q9q.json")
    if not lottie_study:
        lottie_study = load_lottie_url("https://assets9.lottiefiles.com/packages/lf20_x17ybolp.json")

    # Tabs for Inputs
    tab1, tab2, tab3 = st.tabs(["📄 Upload PDF", "✍️ Paste Text", "📸 Upload Image"])
    
    explanation_style = st.session_state.get('explanation_style', 'Simplified') # Default to simplified if not set, or add to sidebar
    
    with tab1:
        uploaded_file = st.file_uploader("Choose a PDF", type="pdf", key="pdf_uploader")
        if uploaded_file and st.button("Analyze PDF 🚀"):
            if lottie_study: st_lottie(lottie_study, height=200, key="loading_pdf")
            with st.spinner("Reading file..."):
                # Use cache for PDF processing
                images = process_pdf(uploaded_file.getvalue())
                st.session_state.pdf_images = images
                st.session_state.text_content = None
                st.session_state.content_type = "image"
                
                if images:
                    prompt = f"I am {st.session_state.student_name}. Explain these slides/pages in a ({explanation_style}) style. Provide 3 review questions. Separate the solution section with ||SPLIT||."
                    resp = get_gemini_response(prompt, images, is_images=True)
                    st.session_state.messages = [{"role": "assistant", "content": resp, "is_split": True}]
                    st.rerun()

    with tab2:
        txt_input = st.text_area("Paste text here:", height=200)
        if st.button("Analyze Text 📝"):
            if txt_input:
                if lottie_study: st_lottie(lottie_study, height=200, key="loading_text")
                with st.spinner("Analyzing text..."):
                    st.session_state.text_content = txt_input
                    st.session_state.pdf_images = None
                    st.session_state.content_type = "text"
                    prompt = f"I am {st.session_state.student_name}. Explain this text in a ({explanation_style}) style. Provide 3 review questions. Separate the solution section with ||SPLIT||."
                    resp = get_gemini_response(prompt, txt_input, is_images=False)
                    st.session_state.messages = [{"role": "assistant", "content": resp, "is_split": True}]
                    st.rerun()

    with tab3:
        uploaded_img = st.file_uploader("Choose an Image", type=["jpg", "png", "jpeg"], key="img_uploader")
        if uploaded_img and st.button("Analyze Image 📸"):
            if lottie_study: st_lottie(lottie_study, height=200, key="loading_img")
            with st.spinner("Scanning image..."):
                try:
                    img = Image.open(uploaded_img)
                    st.session_state.pdf_images = [img] 
                    st.session_state.text_content = None
                    st.session_state.content_type = "image"
                    prompt = f"I am {st.session_state.student_name}. Read the text (handwritten or printed) and explain it in a ({explanation_style}) style. Provide questions and solutions."
                    resp = get_gemini_response(prompt, st.session_state.pdf_images, is_images=True)
                    st.session_state.messages = [{"role": "assistant", "content": resp, "is_split": True}]
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

    # -- Utility Generation Triggers --
    if st.session_state.get("trigger_flashcards"):
        with st.spinner("Generating Flashcards..."):
            flash_prompt = "Extract the top 5 key terms and definitions. Format: Term || Definition"
            if st.session_state.content_type == "image":
                resp = get_gemini_response(flash_prompt, st.session_state.pdf_images, is_images=True)
            else:
                resp = get_gemini_response(f"Context: {st.session_state.text_content}\n\n{flash_prompt}", "", is_images=False)
            st.session_state.messages.append({"role": "assistant", "content": resp, "is_flashcard": True})
            st.session_state.trigger_flashcards = False
            st.rerun()

    if st.session_state.get("trigger_quiz"):
        with st.spinner("Preparing Quiz..."):
            quiz_prompt = """
            Create 3 MCQ questions. Output JSON ONLY:
            [{"question": "..", "options": [".."], "answer": "..", "explanation": ".."}]
            """
            content = st.session_state.pdf_images if st.session_state.content_type == "image" else st.session_state.text_content
            is_img = st.session_state.content_type == "image"
            
            resp = get_gemini_response(quiz_prompt if is_img else f"Context: {content}\n\n{quiz_prompt}", 
                                     content if is_img else "", 
                                     is_images=is_img)
            try:
                cleaned = resp.replace("```json", "").replace("```", "").strip()
                st.session_state.quiz_data = json.loads(cleaned)
            except: st.error("Failed to generate quiz format.")
            st.session_state.trigger_quiz = False
            st.rerun()

    # -- Chat & Interaction Area --
    st.divider()
    
    # Render Quiz
    if st.session_state.quiz_data:
        st.subheader("🧠 Quiz Time")
        score = 0
        for idx, q in enumerate(st.session_state.quiz_data):
            st.markdown(f"**Q{idx+1}: {q['question']}**")
            uc = st.radio("Select Answer:", q['options'], key=f"q_{idx}", index=None)
            if uc:
                if uc == q['answer']:
                    st.success("Correct! ✅")
                    score += 1
                else:
                    st.error(f"Incorrect. Answer: {q['answer']}")
                    st.info(q['explanation'])
            st.write("---")
        if st.button("Finish Quiz"):
             st.balloons() if score == len(st.session_state.quiz_data) else None
             st.success(f"Score: {score}/{len(st.session_state.quiz_data)}")
             st.session_state.quiz_data = None
             st.rerun()

    # Chat Messages
    for i, msg in enumerate(st.session_state.messages):
        role = msg["role"]
        with st.chat_message(role):
            if msg.get("is_flashcard"):
                st.markdown("### 🃏 Flashcards")
                for line in msg["content"].split('\n'):
                    if "||" in line:
                        try:
                            t, d = line.split("||")
                            with st.expander(f"📌 {t}"): st.info(d)
                        except: pass
                if st.button("🔊 Play Audio", key=f"aud_{i}"):
                     aud_bytes = text_to_audio_bytes(msg["content"].replace("||", " means "))
                     if aud_bytes: st.audio(aud_bytes, format='audio/mp3')

            elif msg.get("is_split") or "||SPLIT||" in str(msg["content"]):
                parts = msg["content"].split("||SPLIT||")
                st.markdown(parts[0])
                if st.button("🔊 Play", key=f"aud_{i}"):
                    aud_bytes = text_to_audio_bytes(parts[0])
                    if aud_bytes: st.audio(aud_bytes, format='audio/mp3')
                    
                if len(parts) > 1:
                    with st.expander("👁️ Show Solution/Details"): st.info(parts[1])
            else:
                st.markdown(msg["content"])
                if role == "assistant" and st.button("🔊 Play", key=f"aud_{i}"):
                     aud_bytes = text_to_audio_bytes(msg["content"])
                     if aud_bytes: st.audio(aud_bytes, format='audio/mp3')

    # Chat Input
    # Only enable chat if content is loaded
    if st.session_state.pdf_images or st.session_state.text_content:
        c1, c2 = st.columns([1, 8])
        with c1:
            st.write("") # Spacer
            # Note: speech_to_text might differ in rendering depending on library version
            audio_text = speech_to_text(language='ar', start_prompt="🎤", stop_prompt="⏹️", just_once=True, key='STT')
        
        prompt = audio_text if audio_text else st.chat_input("Ask a follow-up question...")
        
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()

    # Handle Helper Response generation after rerun to show user message immediately
    # (Simple logic: if last message is user, generate response)
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        last_msg = st.session_state.messages[-1]["content"]
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                instr = f"User: {st.session_state.student_name}. Question: {last_msg}. Style: {explanation_style}. Separate solutions with ||SPLIT|| and flashcards with ||FLASH||"
                
                if st.session_state.content_type == "image":
                    resp = get_gemini_response(instr, st.session_state.pdf_images, is_images=True)
                else:
                    resp = get_gemini_response(f"Context: {st.session_state.text_content}\n\n{instr}", "", is_images=False)
                
                is_split = "||SPLIT||" in resp
                is_flash = "||FLASH||" in resp
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": resp, 
                    "is_split": is_split, 
                    "is_flashcard": is_flash
                })
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True) # End main content

    # --- Footer ---
    st.markdown("""
        <div class="footer-container">
            <div class="footer-content">
                <span>Developed by <b>fadhel wisam</b></span>
                <span style="color: #e0e0e0;">|</span>
                <a href="https://www.instagram.com/leavingt0n1ght?igsh=MTk1enRuZnh3M3Nkdw==" target="_blank" class="social-link">
                    📸 Instagram
                </a>
                <a href="https://www.facebook.com/share/17wzPoDcLp/" target="_blank" class="social-link">
                    📘 Facebook
                </a>
            </div>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

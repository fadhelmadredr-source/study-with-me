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
from typing import List, Optional, Union, Any

# --- 1. إعدادات الصفحة ---
PAGE_TITLE = "Study With Me"
PAGE_ICON = "🎓"
LAYOUT = "wide"

# قائمة الموديلات الاحتياطية (راح يجربهم بالسر)
FALLBACK_MODELS = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro", "gemini-pro"]

THEMES = {
    "☀️ Light": {"bg": "#f8f9fa", "text": "#212529", "card": "#ffffff", "sidebar": "#ffffff", "accent": "#1a73e8", "border": "#e0e0e0"},
    "🌑 Dark": {"bg": "#0e1117", "text": "#fafafa", "card": "#262730", "sidebar": "#262730", "accent": "#8ab4f8", "border": "#3d3d3d"},
    "☕ Coffee": {"bg": "#fdf6e3", "text": "#586e75", "card": "#eee8d5", "sidebar": "#eee8d5", "accent": "#b58900", "border": "#d3cbb8"}
}

# --- 2. الإعداد والتهيئة ---
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
        "active_api_key_index": 0,
        "working_model": None # لتخزين الموديل الشغال
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- 3. التصميم ---
def apply_theme(theme_name: str):
    t = THEMES[theme_name]
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&family=Inter:wght@400;600&display=swap');
        :root {{ --primary-color: {t['accent']}; --bg-color: {t['bg']}; --text-color: {t['text']}; --card-bg: {t['card']}; --border-color: {t['border']}; }}
        html, body, [class*="st-"] {{ font-family: 'Cairo', 'Inter', sans-serif !important; }}
        .stApp {{ background-color: {t['bg']}; color: {t['text']}; }}
        section[data-testid="stSidebar"] {{ background-color: {t['sidebar']}; border-right: 1px solid {t['border']}; }}
        .stButton > button {{ background: linear-gradient(135deg, {t['accent']}, {t['accent']}dd); color: {t['bg'] if theme_name != '🌑 Dark' else '#fff'} !important; border-radius: 12px; border: none; font-weight: 600; }}
        .css-card, [data-testid="stExpander"], div.stTabs [data-baseweb="tab-list"] {{ background-color: {t['card']}; border: 1px solid {t['border']}; border-radius: 12px; }}
        h1, h2, h3, h4 {{ color: {t['accent']} !important; }}
        [data-testid="stChatMessage"] {{ background-color: {t['card']}; border: 1px solid {t['border']}; border-radius: 12px; }}
        .footer-container {{ position: fixed; bottom: 0; left: 0; width: 100%; background-color: {t['card']}; border-top: 1px solid {t['border']}; padding: 10px 0; text-align: center; z-index: 999; }}
        .footer-content {{ display: flex; justify-content: center; gap: 20px; font-size: 0.9rem; color: {t['text']}; }}
        .main-content {{ margin-bottom: 70px; }}
        header {{ visibility: visible !important; }} footer {{ visibility: hidden; }}
    </style>
    """, unsafe_allow_html=True)

# --- 4. دوال مساعدة ---
@st.cache_resource(show_spinner=False)
def load_lottie_url(url: str):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else None
    except: return None

@st.cache_data(show_spinner=False)
def process_pdf(file_bytes: bytes) -> Optional[List[Image.Image]]:
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return [Image.open(io.BytesIO(doc.load_page(i).get_pixmap().tobytes("png"))) for i in range(min(5, len(doc)))]
    except: return None

@st.cache_data(show_spinner=False)
def text_to_audio_bytes(text: str) -> Optional[bytes]:
    try:
        if not text.strip(): return None
        tts = gTTS(text=text.replace("*", "").replace("||SPLIT||", ""), lang='ar')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.getvalue()
    except: return None

# --- 5. منطق الذكاء الاصطناعي (الذكي) ---
def get_api_key() -> Optional[str]:
    keys = st.secrets.get("GEMINI_API_KEYS", [])
    if isinstance(keys, str): keys = [keys] # تصحيح اذا كان نص
    if not keys and "GEMINI_API_KEY" in st.secrets: keys = [st.secrets["GEMINI_API_KEY"]]
    if not keys: return None
    return keys[st.session_state.get('active_api_key_index', 0) % len(keys)]

def get_gemini_response(prompt: str, content_data: Any, is_images: bool = True) -> str:
    """يحاول الاتصال بعدة موديلات حتى يجد واحد يعمل"""
    api_key = get_api_key()
    if not api_key: return "⚠️ API Key not found in Secrets."
    genai.configure(api_key=api_key)

    content = [prompt] + content_data if is_images else [prompt + "\n\n" + str(content_data)]
    
    # تحديد قائمة الموديلات للتجربة
    models_to_try = FALLBACK_MODELS
    # اذا كنا نعرف موديل شغال سابقاً، نخليه اول واحد
    if st.session_state.working_model:
        models_to_try = [st.session_state.working_model] + [m for m in FALLBACK_MODELS if m != st.session_state.working_model]

    last_error = ""
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(content)
            
            # اذا نجحنا، نحفظ هذا الموديل للمرات الجاية
            if model_name != st.session_state.working_model:
                st.session_state.working_model = model_name
                # (اختياري) نبلغ المستخدم
                # st.toast(f"Connected using {model_name}", icon="🚀")
            
            return response.text
        except Exception as e:
            last_error = str(e)
            if "429" in last_error or "Quota" in last_error:
                time.sleep(1) # انتظار بسيط اذا السيرفر مشغول
                continue # نجرب الموديل التالي
            
            # اذا الخطأ هو "غير موجود" (404)، نجرب اللي بعده فوراً
            if "not found" in last_error or "404" in last_error:
                continue
    
    return f"❌ All models failed. Last error: {last_error}"

# --- 6. التطبيق الرئيسي ---
def main():
    setup_page()
    init_session_state()
    
    with st.sidebar:
        st.title("Settings ⚙️")
        selected_theme = st.selectbox("Theme:", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.current_theme))
        if selected_theme != st.session_state.current_theme:
            st.session_state.current_theme = selected_theme
            st.rerun()
        
        st.session_state.student_name = st.text_input("Name:", st.session_state.student_name)
        
        # --- قسم التشخيص (Debug) ---
        with st.expander("🛠️ System Status"):
            if st.session_state.working_model:
                st.success(f"Active Model: {st.session_state.working_model}")
            else:
                st.warning("Model: Searching...")
            
            if st.button("Check Available Models"):
                try:
                    key = get_api_key()
                    if key:
                        genai.configure(api_key=key)
                        models = [m.name for m in genai.list_models()]
                        st.write(models)
                    else: st.error("No API Key")
                except Exception as e: st.error(str(e))

        st.divider()
        if st.button("Clear Chat 🗑️"):
            st.session_state.messages = []
            st.session_state.pdf_images = None
            st.session_state.text_content = None
            st.rerun()

    apply_theme(st.session_state.current_theme)

    # المحتوى الرئيسي
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.title("🎓 Study With Me")
    st.caption(f"Hello {st.session_state.student_name}! Ready to learn?")

    lottie_study = load_lottie_url("https://lottie.host/5a67b4eb-d731-417c-9b8b-871a9388319f/7Q0q9q9q9q.json")
    
    tab1, tab2, tab3 = st.tabs(["📄 PDF", "✍️ Text", "📸 Image"])
    
    with tab1:
        uploaded_file = st.file_uploader("Upload PDF", type="pdf")
        if uploaded_file and st.button("Analyze PDF"):
            with st.spinner("Analyzing..."):
                images = process_pdf(uploaded_file.getvalue())
                st.session_state.pdf_images = images
                st.session_state.content_type = "image"
                if images:
                    resp = get_gemini_response(f"I am {st.session_state.student_name}. Explain this.", images, True)
                    st.session_state.messages = [{"role": "assistant", "content": resp}]
                    st.rerun()

    with tab2:
        txt = st.text_area("Paste Text")
        if st.button("Analyze Text") and txt:
            with st.spinner("Analyzing..."):
                st.session_state.text_content = txt
                st.session_state.content_type = "text"
                resp = get_gemini_response(f"I am {st.session_state.student_name}. Explain this.", txt, False)
                st.session_state.messages = [{"role": "assistant", "content": resp}]
                st.rerun()

    with tab3:
        img_file = st.file_uploader("Upload Image", type=["jpg", "png"])
        if img_file and st.button("Analyze Image"):
            with st.spinner("Analyzing..."):
                img = Image.open(img_file)
                st.session_state.pdf_images = [img]
                st.session_state.content_type = "image"
                resp = get_gemini_response(f"I am {st.session_state.student_name}. Explain this.", [img], True)
                st.session_state.messages = [{"role": "assistant", "content": resp}]
                st.rerun()

    # المحادثة
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and st.button("🔊", key=f"tts_{i}"):
                aud = text_to_audio_bytes(msg["content"])
                if aud: st.audio(aud)

    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    # معالجة رد المساعد
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                content = st.session_state.pdf_images if st.session_state.content_type == "image" else st.session_state.text_content
                is_img = st.session_state.content_type == "image"
                resp = get_gemini_response(f"User: {st.session_state.student_name}. Q: {st.session_state.messages[-1]['content']}", content if content else "", is_img)
                st.markdown(resp)
                st.session_state.messages.append({"role": "assistant", "content": resp})
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    
    # الفوتر
    st.markdown("""
        <div class="footer-container">
            <div class="footer-content">
                <span>Developed by <b>fadhel wisam</b></span> | 
                <a href="#" style="color:#1a73e8; text-decoration:none;">Instagram</a> | 
                <a href="#" style="color:#1a73e8; text-decoration:none;">Facebook</a>
            </div>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

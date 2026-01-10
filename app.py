import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai
import io
from gtts import gTTS
import time
from datetime import datetime, timedelta

# --- 1. تصميم الصفحة ---
st.set_page_config(page_title="Study With Me", page_icon="🎓", layout="wide")

custom_css = """
<style>
    .stApp { background-color: #ffffff; color: #000000; }
    h1, h2, h3 { color: #000000 !important; }
    p, li, label, .stMarkdown, .stText { color: #333333 !important; }
    .stButton>button { background-color: #f0f2f6; color: #31333F; border-radius: 8px; border: 1px solid #d6d6d6; }
    .stButton>button:hover { background-color: #e0e2e6; }
    a { color: #0066cc !important; text-decoration: none; }
    
    /* --- كود الإخفاء (جديد) --- */
    /* إخفاء زر Deploy والأيقونات العلوية */
    .stDeployButton {display:none;}
    header {visibility: hidden;}
    
    /* إخفاء فوتر Streamlit الرسمي */
    footer {visibility: hidden;}
    
    /* إخفاء القائمة العلوية (اختياري - اذا ردت تخفي النقاط الثلاثة) */
    /* #MainMenu {visibility: hidden;} */
    
    /* تنسيق العدادات */
    .break-timer {
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        background-color: rgba(0,0,0,0.9); color: white; padding: 50px;
        border-radius: 20px; font-size: 80px; font-weight: bold; z-index: 9999;
        text-align: center; width: 80%;
    }
    .break-title { font-size: 30px; color: #ffcc00; display: block; margin-bottom: 20px; }
    
    .study-timer-box {
        border: 2px solid #4CAF50; background-color: #e8f5e9; color: #2e7d32;
        padding: 10px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 10px;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 2. إدارة الذاكرة والاتصال ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_images" not in st.session_state:
    st.session_state.pdf_images = None
if "study_end_time" not in st.session_state:
    st.session_state.study_end_time = None

# جلب المفتاح من الأسرار
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    selected_model_name = next((m for m in models if 'flash' in m), "models/gemini-1.5-flash")
except Exception as e:
    st.error("⚠️ يرجى التأكد من وضع المفتاح في Secrets.")
    api_key = None
    selected_model_name = None

# --- 3. القائمة الجانبية ---
with st.sidebar:
    st.title("⚙️ الإعدادات")
    st.success(f"✅ الحالة: متصل")

    # المؤقت
    st.markdown("---")
    st.subheader("⏱️ مؤقت التركيز")
    now = datetime.now()
    active_study = False
    
    if st.session_state.study_end_time:
        if now < st.session_state.study_end_time:
            time_left = st.session_state.study_end_time - now
            mins, secs = divmod(int(time_left.total_seconds()), 60)
            st.markdown(f"<div class='study-timer-box'>📚 باقي: {mins}:{secs:02d}</div>", unsafe_allow_html=True)
            active_study = True
            if st.button("إنهاء الجلسة ⏹️"):
                st.session_state.study_end_time = None
                st.rerun()
        else:
            st.session_state.study_end_time = None
            st.success("⏰ انتهت الجلسة!")
            st.balloons()
            st.rerun()
            
    if not active_study:
        timer_mode = st.radio("الوضع:", ("دراسة 📖", "استراحة ☕"), horizontal=True)
        if timer_mode == "دراسة 📖":
            minutes = st.slider("الوقت (دقيقة):", 10, 180, 60)
            if st.button("ابدأ 🚀"):
                st.session_state.study_end_time = now + timedelta(minutes=minutes)
                st.rerun()
        else:
            minutes = st.slider("الوقت (دقيقة):", 1, 60, 15)
            if st.button("استراحة 💤"):
                placeholder = st.empty()
                total_sec = minutes * 60
                for i in range(total_sec):
                    left = total_sec - i
                    m, s = divmod(left, 60)
                    placeholder.markdown(f"<div class='break-timer'><span class='break-title'>☕ استراحة!</span>{m:02d}:{s:02d}</div>", unsafe_allow_html=True)
                    time.sleep(1)
                placeholder.empty()
                st.success("ارجع للدراسة!")

    st.markdown("---")
    explanation_style = st.selectbox("أسلوب الشرح:", ("شرح مبسط (سوالف)", "أكاديمي", "رؤوس أقلام"))

    if st.button("مسح المحادثة 🗑️"):
        st.session_state.messages = []
        st.session_state.pdf_images = None
        st.rerun()

    # حقوق المطور (بدون روابط خارجية مزعجة)
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #666;'>Developed with ❤️ by<br><b>[اكتب اسمك هنا]</b></div>", unsafe_allow_html=True)

# --- 4. الدوال ---
def pdf_to_images(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    images = []
    for page_num in range(min(5, len(doc))):
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        images.append(img)
    return images

def get_gemini_response(prompt, images):
    try:
        model = genai.GenerativeModel(selected_model_name)
        content = [prompt] + images
        response = model.generate_content(content)
        return response.text
    except Exception as e:
        return f"خطأ في الاتصال: {e}"

def text_to_audio(text):
    try:
        clean_text = text.replace("*", "").replace("#", "").replace("-", "")
        tts = gTTS(text=clean_text, lang='ar')
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        return audio_fp
    except:
        return None

# --- 5. الواجهة الرئيسية ---
st.title("Study With Me 🎓")

if not api_key:
    st.error("⛔ يرجى إضافة المفتاح في إعدادات Secrets.")
else:
    uploaded_file = st.file_uploader("ارفع ملف الـ PDF", type="pdf")

    if uploaded_file and st.session_state.pdf_images is None:
        with st.spinner("جاري التحليل..."):
            try:
                st.session_state.pdf_images = pdf_to_images(uploaded_file)
                prompt = f"اشرح المحتوى بأسلوب ({explanation_style}) وضع 3 أسئلة، ثم اكتب ||SPLIT|| ثم الحلول."
                resp = get_gemini_response(prompt, st.session_state.pdf_images)
                st.session_state.messages.append({"role": "assistant", "content": resp, "is_split": True})
            except Exception as e:
                st.error(f"خطأ: {e}")

    # --- 6. الشات ---
    for i, msg in enumerate(st.session_state.messages):
        role = msg["role"]
        with st.chat_message(role):
            if msg.get("is_split"):
                parts = msg["content"].split("||SPLIT||")
                st.markdown(parts[0])
                if st.button("🔊 استمع", key=f"aud_{i}"):
                    aud = text_to_audio(parts[0])
                    if aud: st.audio(aud, format='audio/mp3')
                with st.expander("👁️ الحل"):
                    st.info(parts[1])
            else:
                st.markdown(msg["content"])
                if role == "assistant" and st.button("🔊", key=f"aud_{i}"):
                     aud = text_to_audio(msg["content"])
                     if aud: st.audio(aud, format='audio/mp3')

    if prompt := st.chat_input("اسألني..."):
        if st.session_state.pdf_images:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("..."):
                    resp = get_gemini_response(f"بأسلوب {explanation_style}: {prompt}", st.session_state.pdf_images)
                    st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
            st.rerun()

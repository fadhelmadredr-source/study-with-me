import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai
import io
from gtts import gTTS
import time
from datetime import datetime, timedelta

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="Study With Me", page_icon="🎓", layout="wide")

# --- 2. التصميم (CSS) - التعديل الجديد ---
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; }
    .stApp { background-color: #f8f9fa; color: #212529; }
    
    /* -------------------------------------------------- */
    /* 🎯 منطقة الإخفاء الذكي (Smart Hide) */
    
    /* 1. إبقاء الشريط العلوي ظاهراً (حتى تشتغل النقاط الثلاثة) */
    header { 
        visibility: visible !important; 
    }
    
    /* 2. إخفاء زر Deploy (علامة الصاروخ/GitHub) فقط */
    .stDeployButton {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* 3. إخفاء الفوتر السفلي (Made with Streamlit) */
    footer {
        visibility: hidden !important;
    }
    
    /* 4. إخفاء خيارات التطوير المزعجة من القائمة (اختياري) */
    ul[data-testid="main-menu-list"] > li:first-child {
        display: none !important;
    }
    /* -------------------------------------------------- */

    /* تنسيق العناوين والأزرار */
    h1, h2, h3 { color: #1a73e8 !important; font-weight: 700; text-align: center; }
    .stButton>button {
        background: linear-gradient(45deg, #1a73e8, #0056b3);
        color: white; border: none; border-radius: 12px;
        padding: 10px 24px; font-size: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 8px rgba(0,0,0,0.15); color: white; }
    
    /* تنسيق التبويبات */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px; background-color: #ffffff; padding: 10px; border-radius: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab"] { height: 50px; border-radius: 10px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #e8f0fe !important; color: #1a73e8 !important; }

    section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e0e0e0; }
    .stChatMessage { background-color: #ffffff; border-radius: 15px; border: 1px solid #eee; box-shadow: 0 2px 4px rgba(0,0,0,0.05); padding: 10px; }
    
    .break-timer {
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        background-color: rgba(0,0,0,0.95); color: #fff; padding: 60px;
        border-radius: 30px; font-size: 90px; font-weight: bold; z-index: 9999;
        text-align: center; width: 80%; box-shadow: 0 0 50px rgba(0,0,0,0.5);
    }
    .study-timer-box {
        border: 2px solid #4CAF50; background-color: #e8f5e9; color: #2e7d32;
        padding: 15px; border-radius: 12px; text-align: center; font-weight: bold;
        margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .footer-text { text-align: center; color: #6c757d; font-size: 14px; margin-top: 20px; font-family: 'Cairo', sans-serif; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 3. الذاكرة ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_images" not in st.session_state:
    st.session_state.pdf_images = None
if "text_content" not in st.session_state:
    st.session_state.text_content = None
if "content_type" not in st.session_state:
    st.session_state.content_type = None 
if "study_end_time" not in st.session_state:
    st.session_state.study_end_time = None
if "student_name" not in st.session_state:
    st.session_state.student_name = "يا بطل"

# --- 4. القائمة الجانبية ---
with st.sidebar:
    st.title("⚙️ الإعدادات")
    
    with st.expander("❓ تعليمات المفتاح"):
        st.markdown("احصل عليه من [Google AI Studio](https://aistudio.google.com/app/apikey).")
    
    api_key = st.text_input("مفتاح Gemini API:", type="password")
    
    selected_model_name = None
    if api_key:
        try:
            genai.configure(api_key=api_key)
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            default_index = next((i for i, m in enumerate(models) if 'flash' in m), 0)
            if models:
                st.success("✅ المفتاح شغال")
                selected_model_name = st.selectbox("الموديل:", models, index=default_index)
        except Exception as e:
            st.error(f"المفتاح غير صحيح: {e}")

    st.markdown("---")
    st.subheader("👤 ملف الطالب")
    name_input = st.text_input("اسمك الكريم:", value=st.session_state.student_name)
    if name_input: st.session_state.student_name = name_input
    
    st.markdown("---")
    now = datetime.now()
    active_study = False
    if st.session_state.study_end_time:
        if now < st.session_state.study_end_time:
            time_left = st.session_state.study_end_time - now
            mins, secs = divmod(int(time_left.total_seconds()), 60)
            st.markdown(f"<div class='study-timer-box'>📚 باقي للتركيز<br>{mins}:{secs:02d}</div>", unsafe_allow_html=True)
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
        st.write("⏱️ **مؤقت التركيز:**")
        timer_mode = st.radio("الوضع:", ("دراسة 📖", "استراحة ☕"), horizontal=True, label_visibility="collapsed")
        if timer_mode == "دراسة 📖":
            minutes = st.slider("الوقت (دقيقة):", 10, 180, 60)
            if st.button("ابدأ 🚀"):
                st.session_state.study_end_time = now + timedelta(minutes=minutes)
                st.rerun()
        else:
            minutes = st.slider("الوقت (دقيقة):", 1, 60, 15)
            if st.button("استراحة 💤"):
                ph = st.empty()
                ts = minutes * 60
                for i in range(ts):
                    left = ts - i
                    m, s = divmod(left, 60)
                    ph.markdown(f"<div class='break-timer'><span class='break-title'>☕ ريح عيونك</span>{m:02d}:{s:02d}</div>", unsafe_allow_html=True)
                    time.sleep(1)
                ph.empty()
                st.success("ارجع للدراسة!")

    st.markdown("---")
    explanation_style = st.selectbox("أسلوب الشرح:", ("شرح مبسط (سوالف)", "أكاديمي", "رؤوس أقلام"))

    st.markdown("---")
    chat_history_text = f"مراجعة: {st.session_state.student_name}\nالتاريخ: {datetime.now().strftime('%Y-%m-%d')}\n\n"
    for msg in st.session_state.messages:
        role = "المعلم" if msg["role"] == "assistant" else st.session_state.student_name
        content = str(msg["content"]).replace("||SPLIT||", "\n--- الحلول ---\n")
        chat_history_text += f"[{role}]:\n{content}\n{'='*30}\n"
    st.download_button("📥 تحميل الملخص (TXT)", chat_history_text, f"summary_{st.session_state.student_name}.txt")

    if st.button("مسح المحادثة 🗑️"):
        st.session_state.messages = []
        st.session_state.pdf_images = None
        st.session_state.text_content = None
        st.session_state.content_type = None
        st.rerun()

    st.markdown("---")
    st.markdown("<div class='footer-text'>Designed with 🎨 by<br><b>[اكتب اسمك هنا]</b></div>", unsafe_allow_html=True)

# --- 5. الدوال ---
def pdf_to_images(file):
    try:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        images = []
        for page_num in range(min(5, len(doc))):
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            images.append(img)
        return images
    except: return None

def get_gemini_response(prompt, content_data, is_images=True):
    try:
        model = genai.GenerativeModel(selected_model_name)
        if is_images:
            content = [prompt] + content_data
        else:
            content = [prompt + "\n\n" + content_data]
        response = model.generate_content(content)
        return response.text
    except Exception as e: return f"حدث خطأ: {e}"

def text_to_audio(text):
    try:
        if not text or len(text.strip()) == 0: return None
        clean = text.replace("*", "").replace("#", "").replace("-", "")
        tts = gTTS(text=clean, lang='ar')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except: return None

# --- 6. الواجهة الرئيسية ---
st.markdown("<h1>🎓 Study With Me <br><span style='font-size: 20px; color: #666;'>رفيقك الذكي للدراسة</span></h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📄 رفع ملف (PDF)", "✍️ لصق نص"])

with tab1:
    uploaded_file = st.file_uploader("اختر ملف PDF", type="pdf", key="pdf_uploader")
    if uploaded_file and st.button("تحليل الملف 🚀"):
        if api_key and selected_model_name:
            with st.spinner("جاري قراءة الملف..."):
                st.session_state.pdf_images = pdf_to_images(uploaded_file)
                st.session_state.text_content = None
                st.session_state.content_type = "image"
                if st.session_state.pdf_images:
                    prompt = f"أنا {st.session_state.student_name}. اشرح لي الصور بأسلوب ({explanation_style}) وضع 3 أسئلة، ثم اكتب ||SPLIT|| ثم الحلول."
                    resp = get_gemini_response(prompt, st.session_state.pdf_images, is_images=True)
                    st.session_state.messages = [{"role": "assistant", "content": resp, "is_split": True}]
                    st.rerun()

with tab2:
    txt_input = st.text_area("الصق النص هنا:", height=200)
    if st.button("شرح النص 📝"):
        if txt_input and api_key and selected_model_name:
            with st.spinner("جاري تحليل النص..."):
                st.session_state.text_content = txt_input
                st.session_state.pdf_images = None
                st.session_state.content_type = "text"
                prompt = f"أنا {st.session_state.student_name}. اشرح لي هذا النص بأسلوب ({explanation_style}) وضع 3 أسئلة، ثم اكتب ||SPLIT|| ثم الحلول."
                resp = get_gemini_response(prompt, txt_input, is_images=False)
                st.session_state.messages = [{"role": "assistant", "content": resp, "is_split": True}]
                st.rerun()

# --- 7. الشات ---
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
                if len(parts) > 1: st.info(parts[1])
        else:
            st.markdown(msg["content"])
            if role == "assistant" and st.button("🔊", key=f"aud_{i}"):
                 aud = text_to_audio(msg["content"])
                 if aud: st.audio(aud, format='audio/mp3')

if prompt := st.chat_input("اسألني..."):
    if not (st.session_state.pdf_images or st.session_state.text_content):
        st.warning("يرجى رفع ملف أو لصق نص أولاً!")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("..."):
                chat_prompt = f"المستخدم: {st.session_state.student_name}. السؤال: {prompt}. (الأسلوب: {explanation_style})"
                if st.session_state.content_type == "image":
                    resp = get_gemini_response(chat_prompt, st.session_state.pdf_images, is_images=True)
                else:
                    full_text_context = f"النص الأصلي: {st.session_state.text_content}\n\nالسؤال الجديد: {chat_prompt}"
                    resp = get_gemini_response(full_text_context, "", is_images=False)
                st.markdown(resp)
        st.session_state.messages.append({"role": "assistant", "content": resp})
        st.rerun()

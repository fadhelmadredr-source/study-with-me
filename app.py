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

# --- CSS (التصميم الخاص) ---
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; }
    .stApp { background-color: #f8f9fa; color: #212529; }
    h1, h2, h3 { color: #1a73e8 !important; font-weight: 700; text-align: center; }
    
    .stButton>button {
        background: linear-gradient(45deg, #1a73e8, #0056b3);
        color: white; border: none; border-radius: 12px;
        padding: 10px 24px; font-size: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 8px rgba(0,0,0,0.15); color: white; }
    
    section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e0e0e0; }
    .stChatMessage { background-color: #ffffff; border-radius: 15px; border: 1px solid #eee; box-shadow: 0 2px 4px rgba(0,0,0,0.05); padding: 10px; }
    .stDeployButton, header, footer {visibility: hidden;}

    .break-timer {
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        background-color: rgba(0,0,0,0.95); color: #fff; padding: 60px;
        border-radius: 30px; font-size: 90px; font-weight: bold; z-index: 9999;
        text-align: center; width: 80%; box-shadow: 0 0 50px rgba(0,0,0,0.5);
    }
    .break-title { font-size: 35px; color: #ffca28; display: block; margin-bottom: 20px; }
    
    .study-timer-box {
        border: 2px solid #4CAF50; background-color: #e8f5e9; color: #2e7d32;
        padding: 15px; border-radius: 12px; text-align: center; font-weight: bold;
        margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .footer-text { text-align: center; color: #6c757d; font-size: 14px; margin-top: 20px; font-family: 'Cairo', sans-serif; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 2. إدارة الذاكرة ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_images" not in st.session_state:
    st.session_state.pdf_images = None
if "study_end_time" not in st.session_state:
    st.session_state.study_end_time = None
# متغيرات الطالب الجديدة
if "student_name" not in st.session_state:
    st.session_state.student_name = "يا بطل"

# جلب المفتاح
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    selected_model_name = next((m for m in models if 'flash' in m), "models/gemini-1.5-flash")
except Exception as e:
    st.error("⚠️ يرجى التأكد من وضع المفتاح في Secrets.")
    api_key = None
    selected_model_name = None

# --- 3. القائمة الجانبية (البروفايل) ---
with st.sidebar:
    st.title("👤 ملف الطالب")
    
    # خانة الاسم (للحفظ والترحيب)
    name_input = st.text_input("اسمك الكريم:", value=st.session_state.student_name)
    if name_input:
        st.session_state.student_name = name_input
    
    st.success(f"أهلاً بك، {st.session_state.student_name}!")
    
    st.markdown("---")
    st.subheader("⚙️ الإعدادات")

    # المؤقت
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
                placeholder = st.empty()
                total_sec = minutes * 60
                for i in range(total_sec):
                    left = total_sec - i
                    m, s = divmod(left, 60)
                    placeholder.markdown(f"<div class='break-timer'><span class='break-title'>☕ ريح عيونك</span>{m:02d}:{s:02d}</div>", unsafe_allow_html=True)
                    time.sleep(1)
                placeholder.empty()
                st.success("ارجع للدراسة!")

    st.markdown("---")
    explanation_style = st.selectbox("أسلوب الشرح:", ("شرح مبسط (سوالف)", "أكاديمي", "رؤوس أقلام"))

    # --- ميزة الحفظ (الجديدة) ---
    st.markdown("---")
    st.subheader("💾 حفظ المراجعة")
    
    # تحضير النص للتحميل
    chat_history_text = f"مراجعة الطالب: {st.session_state.student_name}\nالتاريخ: {datetime.now().strftime('%Y-%m-%d')}\n\n"
    for msg in st.session_state.messages:
        role = "المعلم الذكي" if msg["role"] == "assistant" else st.session_state.student_name
        content = msg["content"].replace("||SPLIT||", "\n\n--- الحلول ---\n")
        chat_history_text += f"[{role}]:\n{content}\n\n{'='*40}\n\n"
        
    st.download_button(
        label="📥 تحميل الملخص (TXT)",
        data=chat_history_text,
        file_name=f"study_summary_{st.session_state.student_name}.txt",
        mime="text/plain"
    )

    if st.button("مسح المحادثة 🗑️"):
        st.session_state.messages = []
        st.session_state.pdf_images = None
        st.rerun()

    st.markdown("---")
    st.markdown("<div class='footer-text'>Designed with 🎨 by<br><b>[اكتب اسمك هنا]</b></div>", unsafe_allow_html=True)

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
st.markdown("<h1>🎓 Study With Me <br><span style='font-size: 20px; color: #666;'>رفيقك الذكي للدراسة</span></h1>", unsafe_allow_html=True)

if not api_key:
    st.error("⛔ يرجى إضافة المفتاح في إعدادات Secrets.")
else:
    # رسالة ترحيبية باسم الطالب
    if not st.session_state.pdf_images:
        st.info(f"هلا {st.session_state.student_name}! ارفع الملزمة وخلينا نبدي.")

    uploaded_file = st.file_uploader("ارفع ملف الـ PDF", type="pdf")

    if uploaded_file and st.session_state.pdf_images is None:
        with st.spinner("جاري تحليل الملف... ⏳"):
            try:
                st.session_state.pdf_images = pdf_to_images(uploaded_file)
                prompt = f"مرحبا، أنا الطالب {st.session_state.student_name}. اشرح لي المحتوى بأسلوب ({explanation_style}) وضع 3 أسئلة، ثم اكتب ||SPLIT|| ثم الحلول."
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
                    chat_prompt = f"المستخدم: {st.session_state.student_name}. السؤال: {prompt}. (الأسلوب: {explanation_style})"
                    resp = get_gemini_response(chat_prompt, st.session_state.pdf_images)
                    st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
            st.rerun()

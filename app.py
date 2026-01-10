import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai
import io
from gtts import gTTS
import time
from datetime import datetime, timedelta # مكتبات الوقت الجديدة

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
    
    /* تنسيق عداد الاستراحة الكبير */
    .break-timer {
        position: fixed;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        background-color: rgba(0,0,0,0.9);
        color: white;
        padding: 50px;
        border-radius: 20px;
        font-size: 80px;
        font-weight: bold;
        z-index: 9999;
        text-align: center;
        width: 80%;
    }
    .break-title { font-size: 30px; color: #ffcc00; display: block; margin-bottom: 20px; }
    
    /* تنسيق عداد الدراسة الصغير */
    .study-timer-box {
        border: 2px solid #4CAF50;
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 10px;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
        margin-bottom: 10px;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 2. إدارة الذاكرة ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_images" not in st.session_state:
    st.session_state.pdf_images = None
if "study_end_time" not in st.session_state:
    st.session_state.study_end_time = None # لحفظ وقت انتهاء الدراسة

# --- 3. القائمة الجانبية ---
with st.sidebar:
    st.title("⚙️ الإعدادات")
    
    with st.expander("❓ تعليمات المفتاح"):
        st.markdown("احصل عليه من [Google AI Studio](https://aistudio.google.com/app/apikey).")
    
    api_key = st.text_input("مفتاح Gemini API:", type="password")

    # --- نظام المؤقت الذكي ---
    st.markdown("---")
    st.subheader("⏱️ مؤقت التركيز")
    
    # التحقق: هل هناك جلسة دراسة نشطة؟
    now = datetime.now()
    active_study = False
    
    if st.session_state.study_end_time:
        if now < st.session_state.study_end_time:
            # حساب الوقت المتبقي
            time_left = st.session_state.study_end_time - now
            mins, secs = divmod(int(time_left.total_seconds()), 60)
            st.markdown(f"""
            <div class='study-timer-box'>
                📚 وضع الدراسة نشط<br>
                باقي: {mins} دقيقة و {secs} ثانية
            </div>
            """, unsafe_allow_html=True)
            active_study = True
            if st.button("إنهاء الجلسة ⏹️"):
                st.session_state.study_end_time = None
                st.rerun()
        else:
            # انتهى الوقت
            st.session_state.study_end_time = None
            st.success("⏰ انتهت جلسة الدراسة! حان وقت الراحة.")
            st.balloons()
            st.rerun()
            
    if not active_study:
        timer_mode = st.radio("الوضع:", ("دراسة 📖", "استراحة ☕"), horizontal=True)
        
        if timer_mode == "دراسة 📖":
            minutes = st.slider("مدة الدراسة (دقيقة):", 10, 180, 60)
            if st.button("ابدأ التركيز 🚀"):
                # هنا نستخدم الطريقة الغير مجمدة
                st.session_state.study_end_time = now + timedelta(minutes=minutes)
                st.rerun()
                
        else: # وضع الاستراحة
            minutes = st.slider("مدة الاستراحة (دقيقة):", 1, 60, 15)
            if st.button("ابدأ الاستراحة 💤"):
                # هنا نستخدم الطريقة المجمدة (Blocking Loop)
                placeholder = st.empty()
                total_sec = minutes * 60
                
                for i in range(total_sec):
                    left = total_sec - i
                    m, s = divmod(left, 60)
                    # عرض شاشة سوداء تغطي الموقع
                    placeholder.markdown(f"""
                    <div class='break-timer'>
                        <span class='break-title'>☕ خذ استراحة، لا تشتغل!</span>
                        {m:02d}:{s:02d}
                    </div>
                    """, unsafe_allow_html=True)
                    time.sleep(1) # تجميد النظام ثانية بثانية
                
                placeholder.empty()
                st.success("انتهت الاستراحة! ارجع للدراسة 💪")

    # --- باقي الإعدادات ---
    st.markdown("---")
    explanation_style = st.selectbox(
        "أسلوب الشرح:",
        ("شرح مبسط (سوالف)", "أكاديمي", "رؤوس أقلام")
    )
    
    selected_model_name = None
    if api_key:
        try:
            genai.configure(api_key=api_key)
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            default_ix = next((i for i, m in enumerate(models) if 'flash' in m), 0)
            if models:
                selected_model_name = st.selectbox("الموديل:", models, index=default_ix)
        except:
            pass

    if st.button("مسح المحادثة 🗑️"):
        st.session_state.messages = []
        st.session_state.pdf_images = None
        st.rerun()

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
    model = genai.GenerativeModel(selected_model_name)
    content = [prompt] + images
    response = model.generate_content(content)
    return response.text

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

uploaded_file = st.file_uploader("ارفع ملف الـ PDF", type="pdf")

if uploaded_file and st.session_state.pdf_images is None:
    if api_key and selected_model_name:
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
        st.rerun() # تحديث الصفحة لتحديث عداد الدراسة

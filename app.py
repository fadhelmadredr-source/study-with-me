import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai
import io
from gtts import gTTS
import time  # مكتبة الوقت للمؤقت

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
    /* تنسيق العداد */
    .timer-box {
        font-size: 40px; font-weight: bold; text-align: center; color: #ff4b4b;
        background-color: #f0f0f0; padding: 10px; border-radius: 10px; margin-bottom: 10px;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 2. إدارة الذاكرة ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_images" not in st.session_state:
    st.session_state.pdf_images = None

# --- 3. القائمة الجانبية ---
with st.sidebar:
    st.title("⚙️ الإعدادات")
    
    with st.expander("❓ تعليمات المفتاح"):
        st.markdown("احصل عليه من [Google AI Studio](https://aistudio.google.com/app/apikey).")
    
    api_key = st.text_input("مفتاح Gemini API:", type="password")

    # --- ميزة المؤقت (الجديدة) ---
    st.markdown("---")
    st.subheader("⏱️ مؤقت التركيز")
    
    # اختيار نوع المؤقت (دراسة أو راحة)
    timer_mode = st.radio("الوضع:", ("دراسة 📖", "استراحة ☕"), horizontal=True)
    
    # تحديد الوقت (بالدقائق)
    if timer_mode == "دراسة 📖":
        minutes = st.slider("مدة الدراسة (دقيقة):", 10, 180, 120) # الافتراضي ساعتين
    else:
        minutes = st.slider("مدة الاستراحة (دقيقة):", 5, 60, 30) # الافتراضي نص ساعة

    if st.button("ابدأ المؤقت ⏳"):
        # مكان عرض العداد
        timer_placeholder = st.empty()
        bar = st.progress(0)
        
        total_seconds = minutes * 60
        
        for i in range(total_seconds):
            # حساب الوقت المتبقي
            time_left = total_seconds - i
            mins, secs = divmod(time_left, 60)
            timer_text = f"{mins:02d}:{secs:02d}"
            
            # تحديث الشاشة
            timer_placeholder.markdown(f"<div class='timer-box'>{timer_text}</div>", unsafe_allow_html=True)
            bar.progress((i + 1) / total_seconds)
            time.sleep(1) # انتظار ثانية
            
        # عند انتهاء الوقت
        timer_placeholder.markdown("<div class='timer-box'>⏰ انتهى الوقت!</div>", unsafe_allow_html=True)
        bar.progress(100)
        st.balloons() # احتفال
        st.success("عاشت ايدك! كملت الجلسة بنجاح.")

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
        st.rerun()

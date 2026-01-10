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

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="Study With Me", page_icon="🎓", layout="wide")

# --- 2. التصميم (CSS) ---
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; }
    .stApp { background-color: #f8f9fa; color: #212529; }
    
    header { visibility: visible !important; }
    .stDeployButton { display: none !important; visibility: hidden !important; }
    footer { visibility: hidden !important; }
    ul[data-testid="main-menu-list"] > li:first-child { display: none !important; }

    h1, h2, h3 { color: #1a73e8 !important; font-weight: 700; text-align: center; }
    .stButton>button {
        background: linear-gradient(45deg, #1a73e8, #0056b3);
        color: white; border: none; border-radius: 12px;
        padding: 10px 24px; font-size: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 8px rgba(0,0,0,0.15); color: white; }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px; background-color: #ffffff; padding: 10px; border-radius: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab"] { height: 50px; border-radius: 10px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #e8f0fe !important; color: #1a73e8 !important; }

    section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e0e0e0; }
    
    .study-timer-box {
        border: 2px solid #4CAF50; background-color: #e8f5e9; color: #2e7d32;
        padding: 15px; border-radius: 12px; text-align: center; font-weight: bold;
        margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .footer-text { text-align: center; color: #6c757d; font-size: 14px; margin-top: 20px; font-family: 'Cairo', sans-serif; }
    
    .quiz-container { background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 3. تهيئة الذاكرة ---
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
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None

# --- 4. دوال مساعدة ---
def load_lottieurl(url):
    try:
        r = requests.get(url)
        if r.status_code != 200: return None
        return r.json()
    except: return None

lottie_study = load_lottieurl("https://lottie.host/5a67b4eb-d731-417c-9b8b-871a9388319f/7Q0q9q9q9q.json") 
if not lottie_study:
    lottie_study = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_x17ybolp.json")

def create_html_report(messages, student_name):
    html = f"""
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; background-color: #f9f9f9; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #1a73e8; text-align: center; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            .message {{ margin-bottom: 20px; padding: 15px; border-radius: 10px; }}
            .user {{ background-color: #e8f0fe; color: #1a73e8; border-right: 5px solid #1a73e8; }}
            .bot {{ background-color: #f1f3f4; color: #202124; border-right: 5px solid #34a853; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📄 ملخص مراجعة: {student_name}</h1>
            <p style="text-align: center; color: #666;">التاريخ: {datetime.now().strftime('%Y-%m-%d')}</p>
            <hr>
    """
    for msg in messages:
        role_class = "user" if msg["role"] == "user" else "bot"
        role_name = student_name if msg["role"] == "user" else "المعلم الذكي"
        content = str(msg["content"]).replace("||SPLIT||", "<br><b>--- الحل ---</b><br>").replace("||FLASH||", "")
        if "```json" not in content:
            html += f"""
            <div class="message {role_class}">
                <strong>{role_name}:</strong><br>
                {content}
            </div>
            """
    html += "</div></body></html>"
    return html

# --- 5. القائمة الجانبية ---
with st.sidebar:
    st.title("⚙️ الإعدادات")
    
    api_key = None
    selected_model_name = "models/gemini-1.5-flash"

    try:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            genai.configure(api_key=api_key)
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            if available_models:
                flash_model = next((m for m in available_models if 'flash' in m), None)
                pro_model = next((m for m in available_models if '1.5-pro' in m), None)
                selected_model_name = flash_model if flash_model else (pro_model if pro_model else available_models[0])
        else:
            st.error("⚠️ المفتاح غير موجود في Secrets!")
    except Exception as e:
        st.error(f"⚠️ خطأ: {e}")

    st.subheader("👤 ملف الطالب")
    name_input = st.text_input("اسمك الكريم:", value=st.session_state.student_name)
    if name_input: st.session_state.student_name = name_input
    
    st.markdown("---")
    st.write("🧠 **أدوات ذكية:**")
    
    if st.button("🃏 اصنع بطاقات مراجعة"):
        if st.session_state.pdf_images or st.session_state.text_content:
            st.session_state.messages.append({"role": "user", "content": "اريد بطاقات مراجعة (Flashcards)."})
            st.session_state.trigger_flashcards = True 
            st.rerun()
        else:
            st.toast("⚠️ ارفع ملف أولاً!", icon="📂")

    if st.button("📝 اختبر معلوماتك (Quiz)"):
        if st.session_state.pdf_images or st.session_state.text_content:
            st.session_state.trigger_quiz = True
            st.rerun()
        else:
            st.toast("⚠️ ارفع ملف أولاً!", icon="📂")

    st.markdown("---")
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
    html_report = create_html_report(st.session_state.messages, st.session_state.student_name)
    st.download_button(
        label="📥 تحميل الملخص (HTML ملون)",
        data=html_report,
        file_name=f"study_summary_{st.session_state.student_name}.html",
        mime="text/html"
    )

    if st.button("مسح المحادثة 🗑️"):
        st.session_state.messages = []
        st.session_state.pdf_images = None
        st.session_state.text_content = None
        st.session_state.content_type = None
        st.session_state.quiz_data = None
        st.rerun()

    st.markdown("---")
    st.markdown("<div class='footer-text'>Designed with 🎨 by<br><b>[اكتب اسمك هنا]</b></div>", unsafe_allow_html=True)

# --- 6. الدوال الرئيسية ---
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
        clean = clean.replace("||FLASH||", "").replace("||SPLIT||", "")
        tts = gTTS(text=clean, lang='ar')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except: return None

# --- 7. الواجهة الرئيسية ---
st.markdown("<h1>🎓 Study With Me <br><span style='font-size: 20px; color: #666;'>رفيقك الذكي للدراسة</span></h1>", unsafe_allow_html=True)

if not api_key:
    st.warning("⚠️ الموقع بانتظار تفعيل المفتاح من المطور (Secrets).")
else:
    tab1, tab2 = st.tabs(["📄 رفع ملف (PDF)", "✍️ لصق نص"])

    with tab1:
        uploaded_file = st.file_uploader("اختر ملف PDF", type="pdf", key="pdf_uploader")
        if uploaded_file and st.button("تحليل الملف 🚀"):
            if lottie_study: st_lottie(lottie_study, height=200, key="loading_pdf")
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
            if txt_input:
                if lottie_study: st_lottie(lottie_study, height=200, key="loading_text")
                with st.spinner("جاري تحليل النص..."):
                    st.session_state.text_content = txt_input
                    st.session_state.pdf_images = None
                    st.session_state.content_type = "text"
                    prompt = f"أنا {st.session_state.student_name}. اشرح لي هذا النص بأسلوب ({explanation_style}) وضع 3 أسئلة، ثم اكتب ||SPLIT|| ثم الحلول."
                    resp = get_gemini_response(prompt, txt_input, is_images=False)
                    st.session_state.messages = [{"role": "assistant", "content": resp, "is_split": True}]
                    st.rerun()

    # --- معالجة طلب البطاقات ---
    if "trigger_flashcards" in st.session_state and st.session_state.trigger_flashcards:
        if lottie_study: st_lottie(lottie_study, height=150, key="loading_flash")
        with st.spinner("جاري صناعة البطاقات..."):
            flash_prompt = """
            استخرج أهم 5 مصطلحات وتعاريفها. الصيغة: المصطلح || التعريف
            """
            if st.session_state.content_type == "image":
                resp = get_gemini_response(flash_prompt, st.session_state.pdf_images, is_images=True)
            else:
                context = f"النص: {st.session_state.text_content}\n\n{flash_prompt}"
                resp = get_gemini_response(context, "", is_images=False)
            
            st.session_state.messages.append({"role": "assistant", "content": resp, "is_flashcard": True})
            st.session_state.trigger_flashcards = False
            st.rerun()

    # --- معالجة الكويز ---
    if "trigger_quiz" in st.session_state and st.session_state.trigger_quiz:
        if lottie_study: st_lottie(lottie_study, height=150, key="loading_quiz")
        with st.spinner("جاري إعداد الأسئلة..."):
            quiz_prompt = """
            قم بإنشاء 3 أسئلة اختيار من متعدد (MCQ) من المحتوى.
            يجب أن يكون الإخراج بتنسيق JSON حصراً كالتالي:
            [
                {"question": "السؤال الأول؟", "options": ["ا", "ب", "ج", "د"], "answer": "الجواب الصحيح", "explanation": "التوضيح"},
                ...
            ]
            لا تستخدم Markdown. فقط JSON raw text.
            """
            if st.session_state.content_type == "image":
                resp = get_gemini_response(quiz_prompt, st.session_state.pdf_images, is_images=True)
            else:
                context = f"النص: {st.session_state.text_content}\n\n{quiz_prompt}"
                resp = get_gemini_response(context, "", is_images=False)
            
            try:
                cleaned_json = resp.replace("```json", "").replace("```", "").strip()
                st.session_state.quiz_data = json.loads(cleaned_json)
            except:
                st.error("عذراً، حدث خطأ في بناء الكويز.")
            
            st.session_state.trigger_quiz = False
            st.rerun()

    # --- 8. الشات وعرض الرسائل ---
    for i, msg in enumerate(st.session_state.messages):
        role = msg["role"]
        with st.chat_message(role):
            if msg.get("is_flashcard"):
                st.markdown("### 🃏 بطاقات المراجعة")
                lines = msg["content"].split('\n')
                for line in lines:
                    if "||" in line:
                        try:
                            term, definition = line.split("||")
                            with st.expander(f"📌 {term}"): st.info(definition)
                        except: pass
                if st.button("🔊 اقرأ", key=f"aud_{i}"):
                     aud = text_to_audio(msg["content"].replace("||", " تعني "))
                     if aud: st.audio(aud, format='audio/mp3')

            elif msg.get("is_split") or "||SPLIT||" in str(msg["content"]):
                parts = msg["content"].split("||SPLIT||")
                st.markdown(parts[0])
                if st.button("🔊", key=f"aud_{i}"):
                    aud = text_to_audio(parts[0])
                    if aud: st.audio(aud, format='audio/mp3')
                with st.expander("👁️ الحل"): st.info(parts[1])
            else:
                st.markdown(msg["content"])
                if role == "assistant" and st.button("🔊", key=f"aud_{i}"):
                     aud = text_to_audio(msg["content"])
                     if aud: st.audio(aud, format='audio/mp3')

    # --- عرض الكويز ---
    if st.session_state.quiz_data:
        st.divider()
        st.subheader("🧠 اختبر معلوماتك")
        score = 0
        for idx, q in enumerate(st.session_state.quiz_data):
            st.markdown(f"**س{idx+1}: {q['question']}**")
            user_choice = st.radio(f"اختر الإجابة:", q['options'], key=f"q_{idx}", index=None)
            
            if user_choice:
                if user_choice == q['answer']:
                    st.success("✅ إجابة صحيحة!")
                    score += 1
                else:
                    st.error(f"❌ خطأ. الإجابة الصحيحة: {q['answer']}")
                    st.info(f"💡 توضيح: {q['explanation']}")
            st.write("---")
        
        if st.button("إنهاء الاختبار"):
            final_score = (score / len(st.session_state.quiz_data)) * 100
            if final_score == 100:
                st.balloons()
                st.success(f"🎉 واو! درجة كاملة {score}/{len(st.session_state.quiz_data)}")
            elif final_score >= 50:
                st.success(f"👏 جيد جداً! درجتك {score}/{len(st.session_state.quiz_data)}")
            else:
                st.warning(f"😅 تحتاج مراجعة. درجتك {score}/{len(st.session_state.quiz_data)}")
            st.session_state.quiz_data = None
            st.rerun()

    # --- 9. منطقة الإدخال ---
    if not (st.session_state.pdf_images or st.session_state.text_content):
        st.info("💡 ارفع ملف لتبدأ...")
    else:
        col_mic, col_input = st.columns([1, 8])
        with col_mic:
            st.write("") 
            audio_text = speech_to_text(language='ar', start_prompt="🎤", stop_prompt="⏹️", just_once=True, key='STT')
        
        prompt = audio_text if audio_text else st.chat_input("اسألني...")

        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                if lottie_study: st_lottie(lottie_study, height=100, key="loading_chat")
                with st.spinner("..."):
                    chat_instructions = f"""
                    المستخدم: {st.session_state.student_name}
                    السؤال: {prompt}
                    الأسلوب: {explanation_style}
                    🛑 تعليمات: افصل حلول الكويز بـ ||SPLIT|| وافصل البطاقات بـ ||FLASH||
                    """
                    if st.session_state.content_type == "image":
                        resp = get_gemini_response(chat_instructions, st.session_state.pdf_images, is_images=True)
                    else:
                        full_text_context = f"النص الأصلي: {st.session_state.text_content}\n\n{chat_instructions}"
                        resp = get_gemini_response(full_text_context, "", is_images=False)
                    
                    is_split = "||SPLIT||" in resp
                    is_flash = "||FLASH||" in resp
                    
                    if is_split:
                        parts = resp.split("||SPLIT||")
                        st.markdown(parts[0])
                        with st.expander("👁️ الحل"): st.info(parts[1])
                    elif is_flash:
                        st.markdown(resp)
                    else:
                        st.markdown(resp)
                        
                    st.session_state.messages.append({
                        "role": "assistant", "content": resp, 
                        "is_split": is_split, "is_flashcard": is_flash
                    })
            st.rerun()

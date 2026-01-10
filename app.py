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
import os # مكتبة التعامل مع الملفات للعداد

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="Study With Me", page_icon="🎓", layout="wide")

# --- 2. إعدادات المظهر (Themes) ---
themes = {
    "☀️ نهاري (Light)": {
        "bg": "#f8f9fa", "text": "#212529", "card": "#ffffff", 
        "sidebar": "#ffffff", "accent": "#1a73e8", "border": "#e0e0e0"
    },
    "🌑 ليلي (Dark)": {
        "bg": "#0e1117", "text": "#fafafa", "card": "#262730", 
        "sidebar": "#262730", "accent": "#4da6ff", "border": "#3d3d3d"
    },
    "☕ وضع القراءة (Coffee)": {
        "bg": "#fdf6e3", "text": "#586e75", "card": "#eee8d5", 
        "sidebar": "#eee8d5", "accent": "#b58900", "border": "#d3cbb8"
    }
}

if "current_theme" not in st.session_state:
    st.session_state.current_theme = "☀️ نهاري (Light)"

# --- 3. العداد البسيط (Visitor Counter) ---
def update_visitor_count():
    file_path = "counter.txt"
    # اذا الملف غير موجود، ننشئه ونخلي بي 0
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            f.write("0")
    
    # نقرأ الرقم الحالي
    try:
        with open(file_path, "r") as f:
            count = int(f.read())
    except: count = 0
    
    # نزيد الرقم فقط اذا كانت جلسة جديدة (حتى لا يزيد مع كل ضغطة زر)
    if "visited" not in st.session_state:
        count += 1
        with open(file_path, "w") as f:
            f.write(str(count))
        st.session_state.visited = True
        
    return count

# استدعاء العداد
visitor_count = update_visitor_count()

# --- 4. حقن التصميم ---
def apply_theme(theme_name):
    t = themes[theme_name]
    custom_css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
        html, body, [class*="css"] {{ font-family: 'Cairo', sans-serif; }}
        .stApp {{ background-color: {t['bg']}; color: {t['text']}; }}
        section[data-testid="stSidebar"] {{ background-color: {t['sidebar']}; border-right: 1px solid {t['border']}; }}
        .quiz-container, .stTabs [data-baseweb="tab-list"], .study-timer-box {{
            background-color: {t['card']} !important;
            border: 1px solid {t['border']};
        }}
        h1, h2, h3 {{ color: {t['accent']} !important; font-weight: 700; text-align: center; }}
        p, div, li {{ color: {t['text']}; }}
        .stTabs [data-baseweb="tab"] {{ height: 50px; border-radius: 10px; font-weight: bold; color: {t['text']}; }}
        .stTabs [aria-selected="true"] {{ background-color: {t['bg']} !important; color: {t['accent']} !important; }}
        header {{ visibility: visible !important; }}
        .stDeployButton {{ display: none !important; visibility: hidden !important; }}
        footer {{ visibility: hidden !important; }}
        ul[data-testid="main-menu-list"] > li:first-child {{ display: none !important; }}
        .stButton>button {{
            background: linear-gradient(45deg, {t['accent']}, {t['accent']});
            color: {t['bg'] if theme_name != '🌑 ليلي (Dark)' else '#fff'}; 
            border: none; border-radius: 12px;
            padding: 10px 24px; font-size: 16px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease;
        }}
        .stButton>button:hover {{ transform: translateY(-2px); filter: brightness(110%); }}
        .study-timer-box {{
            border: 2px solid {t['accent']};
            color: {t['accent']};
            padding: 15px; border-radius: 12px; text-align: center; font-weight: bold;
            margin-bottom: 15px;
        }}
        .visitor-box {{
            text-align: center; padding: 10px; margin-top: 20px;
            border-top: 1px solid {t['border']}; color: {t['text']}; opacity: 0.8; font-size: 14px;
        }}
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

# --- 5. تهيئة الذاكرة ---
if "messages" not in st.session_state: st.session_state.messages = []
if "pdf_images" not in st.session_state: st.session_state.pdf_images = None
if "text_content" not in st.session_state: st.session_state.text_content = None
if "content_type" not in st.session_state: st.session_state.content_type = None 
if "study_end_time" not in st.session_state: st.session_state.study_end_time = None
if "student_name" not in st.session_state: st.session_state.student_name = "يا بطل"
if "quiz_data" not in st.session_state: st.session_state.quiz_data = None

# --- 6. دوال مساعدة ---
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
    <body style="font-family: sans-serif; padding: 20px; background-color: #f9f9f9;">
        <h1 style="color: #1a73e8; text-align: center;">📄 ملخص مراجعة: {student_name}</h1>
        <hr>
    """
    for msg in messages:
        role = "الطالب" if msg["role"] == "user" else "المعلم"
        bg = "#e8f0fe" if msg["role"] == "user" else "#f1f3f4"
        content = str(msg["content"]).replace("||SPLIT||", "<br><b>--- الحل ---</b><br>").replace("||FLASH||", "")
        if "```json" not in content:
            html += f"<div style='background:{bg}; padding:10px; margin:10px; border-radius:10px;'><strong>{role}:</strong><br>{content}</div>"
    html += "</body></html>"
    return html

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

# --- دالة الاتصال الذكية (مع ميزة الانتظار التلقائي) ---
def get_gemini_response(prompt, content_data, is_images=True):
    model = genai.GenerativeModel(selected_model_name)
    
    # تجهيز المحتوى
    if is_images:
        content = [prompt] + content_data
    else:
        content = [prompt + "\n\n" + content_data]

    # محاولة الإرسال مع التكرار (Retry Logic)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(content)
            return response.text
        except Exception as e:
            # إذا كان الخطأ هو "تجاوز الحد" (429)
            if "429" in str(e) or "Quota exceeded" in str(e):
                wait_time = 60 # ثانية
                placeholder = st.empty()
                
                # عداد تنازلي لطيف
                for i in range(wait_time, 0, -1):
                    placeholder.warning(f"⏳ السيرفر مشغول (حساب مجاني). ننتظر {i} ثانية ونحاول مرة ثانية...", icon="☕")
                    time.sleep(1)
                
                placeholder.empty() # اخفاء التحذير
                # المحاولة مرة أخرى (Loop will continue)
            else:
                # إذا خطأ ثاني، رجعه فوراً
                return f"حدث خطأ غير متوقع: {e}"
    
    return "❌ فشلت العملية بعد عدة محاولات. يرجى المحاولة لاحقاً."
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

# --- 7. القائمة الجانبية ---
with st.sidebar:
    st.title("⚙️ الإعدادات")
    
    st.subheader("🎨 مظهر التطبيق")
    selected_theme = st.selectbox("اختر لونك المفضل:", list(themes.keys()), index=list(themes.keys()).index(st.session_state.current_theme))
    if selected_theme != st.session_state.current_theme:
        st.session_state.current_theme = selected_theme
        st.rerun()
    apply_theme(st.session_state.current_theme)
    
    st.divider()

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
    except: pass

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
        minutes = st.slider("الوقت (دقيقة):", 10, 120, 45)
        if st.button("ابدأ 🚀"):
            st.session_state.study_end_time = now + timedelta(minutes=minutes)
            st.rerun()

    st.markdown("---")
    explanation_style = st.selectbox("أسلوب الشرح:", ("شرح مبسط (سوالف)", "أكاديمي", "رؤوس أقلام"))

    st.markdown("---")
    html_report = create_html_report(st.session_state.messages, st.session_state.student_name)
    st.download_button("📥 تحميل الملخص (HTML)", html_report, "summary.html", "text/html")

    if st.button("مسح المحادثة 🗑️"):
        st.session_state.messages = []
        st.session_state.pdf_images = None
        st.session_state.text_content = None
        st.session_state.content_type = None
        st.session_state.quiz_data = None
        st.rerun()

    # --- عرض العداد في الفوتر ---
    st.markdown(f"""
    <div class='visitor-box'>
        <b>📊 إحصائيات التطبيق</b><br>
        عدد الزوار: {visitor_count}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='footer-text'>Designed with 🎨 by<br><b>[اكتب اسمك هنا]</b></div>", unsafe_allow_html=True)

# --- 8. الواجهة الرئيسية ---
st.markdown("<h1>🎓 Study With Me <br><span style='font-size: 20px; opacity: 0.7;'>رفيقك الذكي للدراسة</span></h1>", unsafe_allow_html=True)

if not api_key:
    st.warning("⚠️ الموقع بانتظار تفعيل المفتاح من المطور (Secrets).")
else:
    tab1, tab2, tab3 = st.tabs(["📄 رفع ملف (PDF)", "✍️ لصق نص", "📸 صورة (سبورة/دفتر)"])

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

    with tab3:
        uploaded_img = st.file_uploader("اختر صورة", type=["jpg", "png", "jpeg"], key="img_uploader")
        if uploaded_img and st.button("تحليل الصورة 📸"):
            if lottie_study: st_lottie(lottie_study, height=200, key="loading_img")
            with st.spinner("جاري فحص الصورة..."):
                try:
                    img = Image.open(uploaded_img)
                    st.session_state.pdf_images = [img] 
                    st.session_state.text_content = None
                    st.session_state.content_type = "image"
                    prompt = f"أنا {st.session_state.student_name}. اقرأ النص في الصورة (خط يد أو طباعة) واشرحه بأسلوب ({explanation_style}). ثم ضع أسئلة وحلول."
                    resp = get_gemini_response(prompt, st.session_state.pdf_images, is_images=True)
                    st.session_state.messages = [{"role": "assistant", "content": resp, "is_split": True}]
                    st.rerun()
                except Exception as e: st.error(f"خطأ: {e}")

    if "trigger_flashcards" in st.session_state and st.session_state.trigger_flashcards:
        if lottie_study: st_lottie(lottie_study, height=150, key="loading_flash")
        with st.spinner("جاري صناعة البطاقات..."):
            flash_prompt = "استخرج أهم 5 مصطلحات وتعاريفها. الصيغة: المصطلح || التعريف"
            if st.session_state.content_type == "image":
                resp = get_gemini_response(flash_prompt, st.session_state.pdf_images, is_images=True)
            else:
                resp = get_gemini_response(f"النص: {st.session_state.text_content}\n\n{flash_prompt}", "", is_images=False)
            st.session_state.messages.append({"role": "assistant", "content": resp, "is_flashcard": True})
            st.session_state.trigger_flashcards = False
            st.rerun()

    if "trigger_quiz" in st.session_state and st.session_state.trigger_quiz:
        if lottie_study: st_lottie(lottie_study, height=150, key="loading_quiz")
        with st.spinner("جاري إعداد الأسئلة..."):
            quiz_prompt = """
            قم بإنشاء 3 أسئلة MCQ. الإخراج JSON فقط:
            [{"question": "..", "options": [".."], "answer": "..", "explanation": ".."}]
            """
            if st.session_state.content_type == "image":
                resp = get_gemini_response(quiz_prompt, st.session_state.pdf_images, is_images=True)
            else:
                resp = get_gemini_response(f"النص: {st.session_state.text_content}\n\n{quiz_prompt}", "", is_images=False)
            try:
                cleaned = resp.replace("```json", "").replace("```", "").strip()
                st.session_state.quiz_data = json.loads(cleaned)
            except: st.error("خطأ في الكويز")
            st.session_state.trigger_quiz = False
            st.rerun()

    for i, msg in enumerate(st.session_state.messages):
        role = msg["role"]
        with st.chat_message(role):
            if msg.get("is_flashcard"):
                st.markdown("### 🃏 بطاقات")
                for line in msg["content"].split('\n'):
                    if "||" in line:
                        try:
                            t, d = line.split("||")
                            with st.expander(f"📌 {t}"): st.info(d)
                        except: pass
                if st.button("🔊 اقرأ", key=f"aud_{i}"):
                     aud = text_to_audio(msg["content"].replace("||", " هي "))
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

    if st.session_state.quiz_data:
        st.divider()
        st.subheader("🧠 اختبر معلوماتك")
        score = 0
        for idx, q in enumerate(st.session_state.quiz_data):
            st.markdown(f"**س{idx+1}: {q['question']}**")
            uc = st.radio("الإجابة:", q['options'], key=f"q_{idx}", index=None)
            if uc:
                if uc == q['answer']:
                    st.success("✅ صح!")
                    score += 1
                else:
                    st.error(f"❌ خطأ. الصح: {q['answer']}")
                    st.info(q['explanation'])
            st.write("---")
        if st.button("إنهاء"):
            st.balloons() if score == len(st.session_state.quiz_data) else None
            st.success(f"النتيجة: {score}/{len(st.session_state.quiz_data)}")
            st.session_state.quiz_data = None
            st.rerun()

    if st.session_state.pdf_images or st.session_state.text_content:
        c1, c2 = st.columns([1, 8])
        with c1:
            st.write("")
            audio = speech_to_text(language='ar', start_prompt="🎤", stop_prompt="⏹️", just_once=True, key='STT')
        prompt = audio if audio else st.chat_input("اسألني...")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                if lottie_study: st_lottie(lottie_study, height=100, key="loading_chat")
                with st.spinner("..."):
                    instr = f"المستخدم: {st.session_state.student_name}. السؤال: {prompt}. الأسلوب: {explanation_style}. افصل الحلول بـ ||SPLIT|| والبطاقات بـ ||FLASH||"
                    if st.session_state.content_type == "image":
                        resp = get_gemini_response(instr, st.session_state.pdf_images, is_images=True)
                    else:
                        resp = get_gemini_response(f"النص الأصلي: {st.session_state.text_content}\n\n{instr}", "", is_images=False)
                    is_split = "||SPLIT||" in resp
                    is_flash = "||FLASH||" in resp
                    if is_split:
                        p = resp.split("||SPLIT||")
                        st.markdown(p[0])
                        with st.expander("👁️ الحل"): st.info(p[1])
                    else: st.markdown(resp)
                    st.session_state.messages.append({"role": "assistant", "content": resp, "is_split": is_split, "is_flashcard": is_flash})
            st.rerun()
    else:
        st.info("💡 ارفع ملف لتبدأ...")


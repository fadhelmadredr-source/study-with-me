import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai
import io

# --- 1. تصميم الصفحة ---
st.set_page_config(page_title="Study With Me", page_icon="🎓", layout="wide")

custom_css = """
<style>
    .stApp { background-color: #2b2b2b; color: #ffffff; }
    h1, h2, h3 { color: #e0e0e0 !important; }
    p, li, label, .stMarkdown, .stText { color: #cccccc !important; }
    .stButton>button { background-color: #4a4a4a; color: white; border-radius: 10px; border: 1px solid #666; }
    .stButton>button:hover { background-color: #666666; }
    a { color: #4da6ff !important; text-decoration: none; }
    .stChatMessage { background-color: #383838; border-radius: 10px; }
    
    /* تنسيق الفوتر (الحقوق) */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #1f1f1f;
        color: #888;
        text-align: center;
        padding: 10px;
        font-size: 14px;
        z-index: 100;
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
    
    # التعليمات
    with st.expander("❓ ما عندك مفتاح؟ اضغط هنا"):
        st.markdown("""
        1. احصل على المفتاح مجاناً من [Google AI Studio](https://aistudio.google.com/app/apikey).
        2. الصقه في الخانة بالأسفل.
        """)
    
    api_key = st.text_input("مفتاح Gemini API:", type="password")
    
    # --- الميزة رقم 1: اختيار أسلوب الشرح ---
    st.markdown("---")
    st.subheader("🎨 أسلوب المعلم")
    explanation_style = st.selectbox(
        "كيف تحب اشرحلك؟",
        ("شرح مبسط (سوالف عراقية)", "شرح أكاديمي (للامتحان)", "رؤوس أقلام (مراجعة سريعة)", "شرح للأطفال (مبسط جداً)")
    )
    
    # اختيار الموديل
    selected_model_name = None
    if api_key:
        try:
            genai.configure(api_key=api_key)
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            # نختار Flash تلقائياً
            default_ix = next((i for i, m in enumerate(models) if 'flash' in m), 0)
            if models:
                selected_model_name = st.selectbox("الموديل:", models, index=default_ix)
                st.success("✅ المفتاح شغال")
        except:
            st.error("المفتاح غير صحيح")

    # زر المسح
    st.markdown("---")
    if st.button("مسح المحادثة 🗑️"):
        st.session_state.messages = []
        st.session_state.pdf_images = None
        st.rerun()

    # --- الميزة رقم 4: حقوق المطور ---
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #888;'>
    Developed with ❤️ by<br>
    <b>[فاضل وسام فاضل]</b><br>
    <a href='#'>LinkedIn</a> | <a href='#'>GitHub</a>
    </div>
    """, unsafe_allow_html=True)

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

# --- 5. الواجهة الرئيسية والمنطق ---
st.title("Study With Me 🎓")
st.write(f"نظام الشرح المختار: **{explanation_style}**")

uploaded_file = st.file_uploader("ارفع ملف الـ PDF", type="pdf")

if uploaded_file and st.session_state.pdf_images is None:
    if api_key and selected_model_name:
        with st.spinner("جاري تحليل الصور... ⏳"):
            try:
                st.session_state.pdf_images = pdf_to_images(uploaded_file)
                
                # --- الميزة رقم 3: الأمر الذكي (الفاصل السري) ---
                # نطلب من Gemini يفصل الجواب عن الاسئلة بكلمة سرية "||SPLIT||"
                initial_prompt = f"""
                أنت معلم ذكي. اشرح محتوى الصور بأسلوب: ({explanation_style}).
                
                التعليمات:
                1. ابدأ بالشرح المفصل حسب الأسلوب المختار.
                2. ضع 3 أسئلة (MCQ) لاختبار الطالب (بدون وضع الحل مباشرة).
                3. اكتب كلمة "||SPLIT||"
                4. بعد الكلمة، اكتب "الإجابات النموذجية" والحلول الصحيحة.
                
                مهم جداً: لا تكتب الحلول قبل كلمة ||SPLIT||.
                """
                
                full_response = get_gemini_response(initial_prompt, st.session_state.pdf_images)
                
                # تخزين الرد في الذاكرة (مقسم)
                st.session_state.messages.append({"role": "assistant", "content": full_response, "is_split": True})
                
            except Exception as e:
                st.error(f"حدث خطأ: {e}")

# --- 6. عرض المحادثة (مع ميزة إخفاء الجواب) ---
for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message("user"):
            st.markdown(message["content"])
    else:
        with st.chat_message("assistant"):
            # التحقق اذا الرسالة تحتاج تقسيم (ميزة 3)
            if message.get("is_split", False) and "||SPLIT||" in message["content"]:
                parts = message["content"].split("||SPLIT||")
                
                # الجزء الأول: الشرح والأسئلة
                st.markdown(parts[0])
                
                # الجزء الثاني: الأجوبة (داخل زر)
                with st.expander("👁️ إظهار الإجابات الصحيحة"):
                    st.success(parts[1])
            else:
                # رسالة شات عادية
                st.markdown(message["content"])

# --- 7. الشات التفاعلي ---
if prompt := st.chat_input("اسألني عن المادة..."):
    if not st.session_state.pdf_images:
        st.warning("ارفع الملف اول شي!")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("ديكتب..."):
                # نرسل الأسلوب المختار مع كل رسالة عشان يحافظ على الشخصية
                chat_prompt = f"بأسلوب ({explanation_style})، جاوب: {prompt}"
                response_text = get_gemini_response(chat_prompt, st.session_state.pdf_images)
                st.markdown(response_text)
                
        st.session_state.messages.append({"role": "assistant", "content": response_text, "is_split": False})

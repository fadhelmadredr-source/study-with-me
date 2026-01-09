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
    p, li, label, .stMarkdown { color: #cccccc !important; }
    .stButton>button { background-color: #4a4a4a; color: white; border-radius: 10px; border: 1px solid #666; }
    .stButton>button:hover { background-color: #666666; }
    /* لون فقاعات الشات */
    .stChatMessage { background-color: #383838; border-radius: 10px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 2. إدارة الذاكرة (Session State) ---
# نحتاج مخزن حتى نحفظ بي المحادثة والصور عشان ما تختفي من نضغط انتر
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pdf_images" not in st.session_state:
    st.session_state.pdf_images = None

if "chat_model" not in st.session_state:
    st.session_state.chat_model = None

# --- 3. القائمة الجانبية ---
with st.sidebar:
    st.title("⚙️ الإعدادات")
    api_key = st.text_input("مفتاح Gemini API:", type="password")
    
    # اختيار الموديل
    selected_model_name = None
    if api_key:
        try:
            genai.configure(api_key=api_key)
            models_list = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    models_list.append(m.name)
            
            # تحديد الفلاش تلقائياً
            default_index = 0
            for i, m in enumerate(models_list):
                if 'flash' in m:
                    default_index = i
                    break
            
            if models_list:
                selected_model_name = st.selectbox("اختار الموديل:", models_list, index=default_index)
        except Exception as e:
            st.error(f"خطأ: {e}")

    # زر مسح المحادثة
    if st.button("مسح المحادثة وبدء جديد 🗑️"):
        st.session_state.messages = []
        st.session_state.pdf_images = None
        st.rerun()

# --- 4. الدوال ---
def pdf_to_images(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    images = []
    # نقرأ أول 5 صفحات (زدناها شوية)
    for page_num in range(min(5, len(doc))):
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        images.append(img)
    return images

def get_gemini_response(prompt, images, history):
    # نجهز الموديل
    model = genai.GenerativeModel(selected_model_name)
    
    # نصنع سياق المحادثة (الصور + السؤال)
    # ملاحظة: Gemini 1.5 يتذكر الصور، بس هنا ندزها كل مرة لضمان الدقة
    content = [prompt] + images
    
    # نضيف تاريخ المحادثة البسيط (اختياري للتعقيد، هنا نعتمد على السؤال المباشر مع الصور)
    response = model.generate_content(content)
    return response.text

# --- 5. الواجهة الرئيسية ---
st.title("Study With Me 🎓 - المعلم الذكي")

uploaded_file = st.file_uploader("ارفع ملف الـ PDF هنا", type="pdf")

# معالجة الملف عند الرفع لأول مرة
if uploaded_file and st.session_state.pdf_images is None:
    if api_key and selected_model_name:
        with st.spinner("جاري قراءة الملف وتحليله... ⏳"):
            try:
                # 1. تحويل وحفظ الصور في الذاكرة
                st.session_state.pdf_images = pdf_to_images(uploaded_file)
                
                # 2. إرسال الطلب الأول (الشرح الأولي)
                initial_prompt = """
                أنت معلم خصوصي عراقي ذكي. 
                اشرح لي محتوى هذه الصور بأسلوب مبسط وممتع.
                ثم ضع 3 أسئلة MCQ لاختباري.
                """
                # إضافة رسالة الترحيب من النظام
                response = get_gemini_response(initial_prompt, st.session_state.pdf_images, [])
                
                # حفظ الرسالة في سجل الشات
                st.session_state.messages.append({"role": "assistant", "content": response})
                
            except Exception as e:
                st.error(f"حدث خطأ: {e}")
    else:
        st.warning("يرجى إدخال المفتاح أولاً!")

# --- 6. عرض الشات (Chat Interface) ---

# عرض الرسائل السابقة
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# مكان الكتابة (Input)
if prompt := st.chat_input("اسألني أي شيء عن الملزمة..."):
    # 1. عرض رسالة المستخدم
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. معالجة رد الذكاء الاصطناعي
    if st.session_state.pdf_images:
        with st.chat_message("assistant"):
            with st.spinner("ديفكر... 🤔"):
                # نعدل البرومبت ليكون ضمن سياق الشات
                chat_prompt = f"""
                بناءً على الصور المرفقة (الملزمة)، جاوب على سؤال الطالب:
                السؤال: {prompt}
                
                خلي جوابك باللهجة العراقية الودودة والمشجعة.
                """
                response_text = get_gemini_response(chat_prompt, st.session_state.pdf_images, st.session_state.messages)
                st.markdown(response_text)
                
        # حفظ رد المساعد
        st.session_state.messages.append({"role": "assistant", "content": response_text})
    else:
        st.error("يرجى رفع الملف أولاً!")
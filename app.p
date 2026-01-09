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
    /* لون الروابط */
    a { color: #4da6ff !important; text-decoration: none; }
    a:hover { text-decoration: underline; }
    /* لون فقاعات الشات */
    .stChatMessage { background-color: #383838; border-radius: 10px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 2. إدارة الذاكرة ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_images" not in st.session_state:
    st.session_state.pdf_images = None

# --- 3. القائمة الجانبية (مع التعليمات الجديدة) ---
with st.sidebar:
    st.title("⚙️ الإعدادات")
    
    # --- قسم التعليمات (الجديد) ---
    with st.expander("❓ ما عندك مفتاح؟ اضغط هنا للتعليمات"):
        st.markdown("""
        ### خطوات الحصول على المفتاح (مجاناً):
        1. ادخل على موقع **Google AI Studio** [بالضغط هنا](https://aistudio.google.com/app/apikey).
        2. سجل دخول بحساب Google (Gmail) العادي.
        3. اضغط على زر **Create API Key**.
        4. انسخ المفتاح الطويل والصقه بالخانة في الأسفل 👇.
        
        ---
        **💡 أي موديل اختار؟**
        من تطلعلك القائمة، اختار الموديل اللي يحتوي على كلمة **Flash** (مثلاً `gemini-1.5-flash`) لأنه:
        * سريع جداً ⚡.
        * يدعم قراءة الصور والملازم بدقة.
        """)
    
    # --- إدخال المفتاح ---
    api_key = st.text_input("لصق مفتاح Gemini API هنا:", type="password")
    
    # --- اختيار الموديل ---
    selected_model_name = None
    if api_key:
        try:
            genai.configure(api_key=api_key)
            models_list = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    models_list.append(m.name)
            
            # البحث عن Flash وتحديده تلقائياً
            default_index = 0
            for i, m in enumerate(models_list):
                if 'flash' in m:
                    default_index = i
                    break
            
            if models_list:
                st.success("✅ المفتاح شغال!")
                selected_model_name = st.selectbox("اختار الموديل (ننصح بـ Flash):", models_list, index=default_index)
            else:
                st.error("لم يتم العثور على موديلات.")
        except Exception as e:
            st.error(f"المفتاح غير صحيح: {e}")

    # زر مسح المحادثة
    st.markdown("---")
    if st.button("مسح المحادثة وبدء جديد 🗑️"):
        st.session_state.messages = []
        st.session_state.pdf_images = None
        st.rerun()

# --- 4. الدوال ---
def pdf_to_images(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    images = []
    # نقرأ أول 5 صفحات
    for page_num in range(min(5, len(doc))):
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        images.append(img)
    return images

def get_gemini_response(prompt, images, history):
    model = genai.GenerativeModel(selected_model_name)
    content = [prompt] + images
    response = model.generate_content(content)
    return response.text

# --- 5. الواجهة الرئيسية ---
st.title("Study With Me 🎓 - المعلم الذكي")

uploaded_file = st.file_uploader("ارفع ملف الـ PDF هنا (صور أو نص)", type="pdf")

if uploaded_file and st.session_state.pdf_images is None:
    if api_key and selected_model_name:
        with st.spinner("جاري قراءة الملزمة وتحليلها... ⏳"):
            try:
                st.session_state.pdf_images = pdf_to_images(uploaded_file)
                
                initial_prompt = """
                أنت معلم خصوصي عراقي ذكي ومشجع. 
                المطلوب:
                1. شرح مبسط جداً لمحتوى هذه الصور (باللهجة العراقية).
                2. وضع 3 أسئلة (MCQ) لاختبار فهمي.
                """
                response = get_gemini_response(initial_prompt, st.session_state.pdf_images, [])
                st.session_state.messages.append({"role": "assistant", "content": response})
                
            except Exception as e:
                st.error(f"حدث خطأ: {e}")
    else:
        st.info("👈 يرجى إدخال المفتاح في القائمة الجانبية لبدء التحليل.")

# --- 6. الشات ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("اسألني أي سؤال عن الملزمة..."):
    if not st.session_state.pdf_images:
        st.warning("ارفع الملف اول شي! 📂")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("ديكتب... ✍️"):
                chat_prompt = f"جاوب على سؤال الطالب بخصوص الصور المرفقة: {prompt}"
                response_text = get_gemini_response(chat_prompt, st.session_state.pdf_images, st.session_state.messages)
                st.markdown(response_text)
                
        st.session_state.messages.append({"role": "assistant", "content": response_text})

import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai
import io
from gtts import gTTS  # مكتبة الصوت الجديدة

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
    
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: #f9f9f9; color: #555; text-align: center;
        padding: 10px; font-size: 14px; border-top: 1px solid #ddd; z-index: 100;
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
    
    with st.expander("❓ ما عندك مفتاح؟ اضغط هنا"):
        st.markdown("1. احصل عليه من [Google AI Studio](https://aistudio.google.com/app/apikey).\n2. الصقه بالأسفل.")
    
    api_key = st.text_input("مفتاح Gemini API:", type="password")
    
    st.markdown("---")
    st.subheader("🎨 أسلوب المعلم")
    explanation_style = st.selectbox(
        "كيف تحب اشرحلك؟",
        ("شرح مبسط (سوالف عراقية)", "شرح أكاديمي (للامتحان)", "رؤوس أقلام (مراجعة سريعة)", "شرح للأطفال (مبسط جداً)")
    )
    
    selected_model_name = None
    if api_key:
        try:
            genai.configure(api_key=api_key)
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            default_ix = next((i for i, m in enumerate(models) if 'flash' in m), 0)
            if models:
                selected_model_name = st.selectbox("الموديل:", models, index=default_ix)
                st.success("✅ المفتاح شغال")
        except:
            st.error("المفتاح غير صحيح")

    st.markdown("---")
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

# --- دالة تحويل النص إلى صوت ---
def text_to_audio(text):
    try:
        # تنظيف النص من الرموز المزعجة قبل القراءة
        clean_text = text.replace("*", "").replace("#", "").replace("-", "")
        # إنشاء ملف صوتي في الذاكرة
        tts = gTTS(text=clean_text, lang='ar')
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        return audio_fp
    except Exception as e:
        return None

# --- 5. الواجهة الرئيسية ---
st.title("Study With Me 🎓")
st.write(f"نظام الشرح المختار: **{explanation_style}**")

uploaded_file = st.file_uploader("ارفع ملف الـ PDF", type="pdf")

if uploaded_file and st.session_state.pdf_images is None:
    if api_key and selected_model_name:
        with st.spinner("جاري تحليل الصور... ⏳"):
            try:
                st.session_state.pdf_images = pdf_to_images(uploaded_file)
                
                initial_prompt = f"""
                أنت معلم ذكي. اشرح محتوى الصور بأسلوب: ({explanation_style}).
                
                التعليمات:
                1. ابدأ بالشرح المفصل.
                2. ضع 3 أسئلة (MCQ) لاختبار الطالب.
                3. اكتب كلمة "||SPLIT||"
                4. بعد الكلمة، اكتب الحلول الصحيحة.
                """
                
                full_response = get_gemini_response(initial_prompt, st.session_state.pdf_images)
                st.session_state.messages.append({"role": "assistant", "content": full_response, "is_split": True})
                
            except Exception as e:
                st.error(f"حدث خطأ: {e}")

# --- 6. عرض المحادثة (مع الصوت) ---
for i, message in enumerate(st.session_state.messages):
    if message["role"] == "user":
        with st.chat_message("user"):
            st.markdown(message["content"])
    else:
        with st.chat_message("assistant"):
            content_to_show = message["content"]
            audio_text = content_to_show # النص اللي راح ينقري
            
            # معالجة التقسيم (الأسئلة والأجوبة)
            if message.get("is_split", False) and "||SPLIT||" in message["content"]:
                parts = message["content"].split("||SPLIT||")
                content_to_show = parts[0]
                audio_text = parts[0] # نقرأ بس الشرح والأسئلة (بدون الحل)
                
                st.markdown(content_to_show)
                
                # زر تشغيل الصوت للشرح
                if st.button(f"🔊 استمع للشرح", key=f"audio_{i}"):
                    with st.spinner("جاري توليد الصوت..."):
                        audio_file = text_to_audio(audio_text)
                        if audio_file:
                            st.audio(audio_file, format='audio/mp3')
                
                # إظهار الحلول المخفية
                with st.expander("👁️ إظهار الإجابات الصحيحة"):
                    st.info(parts[1])
            else:
                # رسالة عادية
                st.markdown(content_to_show)
                if st.button(f"🔊 قراءة الرد", key=f"audio_{i}"):
                    with st.spinner("جاري توليد الصوت..."):
                        audio_file = text_to_audio(content_to_show)
                        if audio_file:
                            st.audio(audio_file, format='audio/mp3')

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
                chat_prompt = f"بأسلوب ({explanation_style})، جاوب: {prompt}"
                response_text = get_gemini_response(chat_prompt, st.session_state.pdf_images)
                st.markdown(response_text)
                
        st.session_state.messages.append({"role": "assistant", "content": response_text, "is_split": False})
        st.rerun() # إعادة تحميل الصفحة لإظهار زر الصوت الجديد

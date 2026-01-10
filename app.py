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

# --- 2. التصميم (CSS) ---
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; }
    .stApp { background-color: #f8f9fa; color: #212529; }
    
    /* اخفاء العناصر غير المرغوبة */
    [data-testid="stToolbar"] { display: none !important; }
    header { visibility: hidden !important; }
    footer { visibility: hidden !important; }

    /* تنسيق العناوين والأزرار */
    h1, h2, h3 { color: #1a73e8 !important; font-weight: 700; text-align: center; }
    .stButton>button {
        background: linear-gradient(45deg, #1a73e8, #0056b3);
        color: white; border: none; border-radius: 12px;
        padding: 10px 24px; font-size: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 8px rgba(0,0,0,0.15); color: white; }
    
    /* تنسيق التبويبات (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #ffffff;
        padding: 10px;
        border-radius: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        border-radius: 10px;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e8f0fe !important;
        color: #1a73e8 !important;
    }

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
if "text_content" not in st.session_state: # متغير جديد للنصوص
    st.session_state.text_content = None
if "content_type" not in st.session_state: # لتحديد النوع (صور أو نص)
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
    
    # اختيار الموديل
    selected_model_name = None
    if api_key:
        try:
            genai.configure(api_key=api_key)
            models =

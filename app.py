import streamlit as st
import google.generativeai as genai
import PyPDF2
import os

# הגדרות יישור לימין (RTL)
st.set_page_config(page_title="מרכז ידע הנדסי - אביתר", layout="wide")
st.markdown("""<style>body, [data-testid="stSidebar"] { direction: RTL; text-align: right; } p, li, h1, h2, h3, h4, h5, h6 { direction: RTL; text-align: right; }</style>""", unsafe_allow_html=True)

def setup_genai():
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        return True
    return False

def get_available_model():
    """פונקציה שבודקת אילו מודלים זמינים עבור המפתח שלך"""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # ננסה קודם את המודלים הכי חזקים שסביר שיש לך ב-2026
        for preferred in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-2.0-flash', 'models/gemini-pro']:
            if preferred in available_models:
                return preferred
        return available_models[0] if available_models else None
    except:
        return None

def get_pdf_text():
    text = ""
    pdf_folder = "pdfs"
    if not os.path.exists(pdf_folder):
        os.makedirs(pdf_folder)
        return ""
    files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]
    for filename in files:
        with open(os.path.join(pdf_folder, filename), 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    return text

st.title("🤖 מרכז ידע הנדסי חכם")

if not setup_genai():
    st.error("🚨 ה-API Key לא מוגדר ב-Secrets!")
    st.stop()

# ניסיון למצוא מודל עובד
model_name = get_available_model()

if not model_name:
    st.error("🚨 לא נמצאו מודלים זמינים עבור המפתח הזה. וודא שהמפתח תקין.")
    st.stop()

categories = {
    "זיווד אלקטרוני ואטימה": "סכם באופן מקיף את כל עקרונות האטימה ותקני IP.",
    "ניהול תרמי ופיזור חום": "סכם את כל שיטות קירור המארזים וחומרי TIM.",
    "כרטיסי RF ואנטנות": "רכז מידע על תכן מכני לכרטיסי RF וסיכוך."
}

category = st.sidebar.selectbox("בחר קטגוריה:", list(categories.keys()))
st.sidebar.info(f"מודל פעיל: {model_name}")

if st.sidebar.button("הפק סיכום מהמאגר"):
    with st.spinner("מנתח מסמכים..."):
        all_content = get_pdf_text()
        if all_content.strip():
            try:
                model = genai.GenerativeModel(model_name)
                prompt = f"התבסס אך ורק על המידע הבא: \n{all_content[:20000]}\n\n משימה: {categories[category]}"
                response = model.generate_content(prompt)
                st.header(category)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"שגיאה בהפקת הסיכום: {e}")
        else:
            st.warning("תיקיית ה-pdfs ריקה. העלה קבצים ל-GitHub.")

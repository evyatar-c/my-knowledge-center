import streamlit as st
import google.generativeai as genai
import PyPDF2
import os

# הגדרות יישור לימין (RTL)
st.set_page_config(page_title="מרכז ידע הנדסי חכם", layout="wide")
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
        direction: RTL;
        text-align: right;
    }
    p, li, h1, h2, h3, h4, h5, h6 {
        direction: RTL;
        text-align: right;
    }
    </style>
    """, unsafe_allow_html=True)

# פונקציה לבדיקת והגדרת ה-API Key
def setup_genai():
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        return True
    return False

# פונקציה לקריאת ה-PDF
def get_pdf_text():
    text = ""
    pdf_folder = "pdfs"
    if not os.path.exists(pdf_folder):
        os.makedirs(pdf_folder)
        return ""
    
    files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]
    if not files:
        return ""
        
    for filename in files:
        try:
            with open(os.path.join(pdf_folder, filename), 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    content = page.extract_text()
                    if content:
                        text += content + "\n"
        except Exception as e:
            st.error(f"שגיאה בקריאת הקובץ {filename}: {e}")
    return text

st.title("🤖 מרכז ידע הנדסי מבוסס AI")

if not setup_genai():
    st.error("🚨 ה-API Key לא מוגדר ב-Secrets של Streamlit!")
    st.info("לך להגדרות האפליקציה ב-Streamlit Cloud, בחר ב-Secrets והדבק שם: GOOGLE_API_KEY = 'המפתח_שלך'")
    st.stop()

# קטגוריות
categories = {
    "זיווד אלקטרוני ואטימה": "סכם באופן מקיף את כל עקרונות האטימה, סוגי אטמים ותקני IP המופיעים במסמכים.",
    "ניהול תרמי ופיזור חום": "סכם את כל שיטות קירור המארזים, חומרי TIM וחישובי מעבר חום מהמקורות.",
    "כרטיסי RF ואנטנות": "רכז את כל המידע על תכן מכני לכרטיסי RF, סיכוך אלקטרומגנטי והתקנת אנטנות."
}

category = st.sidebar.selectbox("בחר קטגוריה לסיכום מקיף:", list(categories.keys()))

if st.sidebar.button("הפק סיכום מהמאגר"):
    with st.spinner("סורק מסמכים ומנתח..."):
        all_content = get_pdf_text()
        
        if all_content.strip():
            try:
                # שימוש בשם מודל רשמי ומעודכן
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = f"""
                אתה מהנדס מכונות בכיר. התבסס אך ורק על המידע הבא מהמאגר המקצועי:
                ---
                {all_content[:30000]} 
                ---
                משימה: {categories[category]}
                כתוב את הסיכום בעברית טכנית, מסודר עם כותרות ובולטים.
                """
                
                response = model.generate_content(prompt)
                
                st.header(category)
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"שגיאה בתקשורת עם הבינה המלאכותית: {e}")
                st.info("נסה לבדוק אם ה-API Key שלך בתוקף ב-Google AI Studio.")
        else:
            st.warning("לא נמצא טקסט בתיקיית ה-PDFs. וודא שהעלית קבצים לתיקיית pdfs ב-GitHub.")

st.sidebar.divider()
st.sidebar.info("האפליקציה סורקת את הקבצים שנמצאים בתיקיית pdfs בתוך ה-GitHub שלך.")

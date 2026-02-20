import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi

# --- 1. הגדרות עיצוב ויישור לימין (RTL) ---
st.set_page_config(page_title="מרכז ידע הנדסי - אביתר", layout="wide")
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
        direction: RTL;
        text-align: right;
    }
    p, li, h1, h2, h3, h4, h5, h6, span, label {
        direction: RTL;
        text-align: right;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות עזר למשיכת מידע ---

def get_url_text(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]): script.decompose()
        return f"\n--- תוכן מהאתר {url} ---\n" + soup.get_text()
    except: return ""

def get_youtube_text(url):
    try:
        if "v=" in url: video_id = url.split("v=")[1].split("&")[0]
        else: video_id = url.split("/")[-1]
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['he', 'en'])
        text = " ".join([t['text'] for t in transcript])
        return f"\n--- תמלול מיוטיוב {url} ---\n" + text
    except: return ""

def get_pdf_text():
    text = ""
    pdf_folder = "pdfs"
    if os.path.exists(pdf_folder):
        files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]
        for filename in files:
            try:
                with open(os.path.join(pdf_folder, filename), 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        content = page.extract_text()
                        if content: text += content + "\n"
            except: continue
    return text

def get_links_content():
    combined_text = ""
    if os.path.exists('links.txt'):
        with open('links.txt', 'r', encoding='utf-8') as f:
            for link in f.readlines():
                link = link.strip()
                if not link: continue
                if "youtube.com" in link or "youtu.be" in link:
                    combined_text += get_youtube_text(link)
                else:
                    combined_text += get_url_text(link)
    return combined_text

def find_gemini_3_model():
    """סורק ומוצא אך ורק מודלים ממשפחת Gemini 3"""
    try:
        # קבלת רשימת המודלים התומכים ביצירת תוכן
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # סינון קפדני: רק מודלים המכילים "gemini-3" בשם שלהם
        gemini_3_models = [m for m in available if 'gemini-3' in m]
        
        if not gemini_3_models:
            return None
            
        # סדר עדיפויות בתוך משפחת Gemini 3
        for preferred in ['models/gemini-3-pro', 'models/gemini-3-flash']:
            if preferred in gemini_3_models:
                return preferred
        
        return gemini_3_models[0] # החזרת הראשון שנמצא אם המועדפים לא קיימים
    except Exception as e:
        return None

# --- 3. לוגיקה מרכזית ---

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🚨 חסר API Key בתיקיית ה-Secrets של Streamlit!")
    st.stop()

st.title("🤖 מרכז ידע הנדסי - Gemini 3 בלבד")

# איתור מודל Gemini 3 בלבד
working_model = find_gemini_3_model()

# רשימת הקטגוריות המלאה מהסילבוס
categories = {
    "איפיון דרישות, אימות ותיקוף (V&V)": "פרט לעומק על PRD/TRD, מודל ה-V, Verification מול Validation וגזירת דרישות.",
    "שלבי פיתוח מוצר ובדיקות": "הרחב מאוד על PDR, CDR, NPI, ובדיקות ATP, QTP ו-ESS כולל מתודולוגיות.",
    "ניהול סיכונים הנדסי": "סכם בפירוט רב ניהול סיכונים טכני, FMEA ודגמי היתכנות POD.",
    "טכנולוגיות ייצור": "פרט על CNC, יציקות, DFM והדפסות תלת-ממד כולל שיקולי בחירה הנדסיים.",
    "סובלנויות ו-GD&T": "פרט לעומק על בקרות גיאומטריות, צבירת טולרנסים RSS/Worst Case והתאמות Fits.",
    "קורוזיה, ציפויים וטיפולי שטח": "סכם בהרחבה מנגנוני קורוזיה, בחירת ציפויים ומניעת היתפסות (Galling).",
    "תכן לאטימות (IP & EMI)": "פרט לעומק על אטימה סביבתית, סיכוך EMI, חריצים ואטמים.",
    "שיקולי תכן תרמי": "הרחב מאוד על מנגנוני העברת חום, ניהול תרמי במארזים וחישובי טמפרטורת צומת.",
    "תכן פלסטיק וחומרים": "סכם תכן להזרקת פלסטיק, זוויות חליצה, פגמים ופולימרים הנדסיים.",
    "תכן כרטיסים אלקטרוניים (PCB)": "פרט לעומק על זיווד כרטיסים, Rigid-Flex ומגבלות ייצור.",
    "היבטי עלות וניהול פרויקט": "סכם תהליכי DTC, שימוש ב-COTS ומבנה תוכניות עבודה (גאנט).",
    "אנליזות וחישובים הנדסיים": "פרט על אנליזות Von Mises, רעידות והלמים וחישובים תרמו-מכניים.",
    "תכן להרכבתיות ואמינות (DFA/DFS)": "סכם שיטות לצמצום טעויות הרכבה, נגישות לכלי עבודה ותחזוקתיות."
}

# תפריט צד
st.sidebar.header("הגדרות וניווט")
if working_model:
    st.sidebar.success(f"מודל Gemini 3 פעיל: {working_model}")
else:
    st.sidebar.error("🚨 לא נמצא מודל Gemini 3 זמין בחשבון זה. האפליקציה דורשת Gemini 3 ומעלה.")
    st.stop()

category = st.sidebar.selectbox("בחר נושא לסיכום מפורט:", list(categories.keys()))

if st.sidebar.button("הפק סיכום מקיף ומפורט"):
    with st.spinner("Gemini 3 מנתח את כל המאגר (PDF + אתרים + יוטיוב)..."):
        content = get_pdf_text() + get_links_content()
        
        if content.strip():
            try:
                model = genai.GenerativeModel(working_model)
                prompt = f"""
                אתה מהנדס מכונות בכיר ומדריך טכני המשתמש ביכולות Gemini 3 לניתוח מעמיק.
                משימה: כתוב סיכום **ארוך מאוד, מפורט, מקצועי ומעמיק** על הנושא הבא: {category}.
                
                הנחיות קריטיות:
                1. התבסס אך ורק על המידע מהמקורות שסופקו (PDF, אתרים ותמלולי יוטיוב).
                2. הסבר בהרחבה את הלוגיקה ההנדסית ("הלמה" וה"איך").
                3. חלק את התשובה לכותרות ברורות, תתי-כותרות ורשימות בולטים ארוכות ומפורטות.
                4. אל תחסוך במילים! אני זקוק לכל פרט טכני, נוסחה, תקן או דוגמה שמופיעים במקורות.
                5. ספק תשובה ברמת Senior Mechanical Engineer להכנה לראיון עבודה.
                
                המקורות:
                ---
                {content[:250000]}
                ---
                כתוב בעברית טכנית ברמה גבוהה מאוד.
                """
                response = model.generate_content(prompt)
                st.header(category)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"שגיאה בהפקת התוכן: {e}")
        else:
            st.warning("לא נמצא תוכן במקורות שלך ב-GitHub (תיקיית pdfs או קובץ links.txt).")

st.sidebar.divider()
st.sidebar.caption("מבוסס על המאגר הקבוע ב-GitHub")

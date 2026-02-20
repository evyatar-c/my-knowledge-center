import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi

# --- 1. הגדרות עיצוב ויישור לימין (RTL) ---
st.set_page_config(page_title="מרכז ידע הנדסי - אביתר", layout="wide")
st.markdown("""<style>body, [data-testid="stSidebar"] { direction: RTL; text-align: right; } p, li, h1, h2, h3, h4, h5, h6 { direction: RTL; text-align: right; }</style>""", unsafe_allow_html=True)

# --- 2. פונקציות למשיכת מידע ממקורות שונים ---

def get_url_text(url):
    """מושך טקסט מאתרי אינטרנט"""
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]): script.decompose()
        return f"\n--- תוכן מהאתר {url} ---\n" + soup.get_text()
    except: return ""

def get_youtube_text(url):
    """מושך תמלול מסרטוני יוטיוב"""
    try:
        # חילוץ מזהה הסרטון
        if "v=" in url: video_id = url.split("v=")[1].split("&")[0]
        else: video_id = url.split("/")[-1]
        
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['he', 'en'])
        text = " ".join([t['text'] for t in transcript])
        return f"\n--- תמלול מיוטיוב {url} ---\n" + text
    except: return ""

def get_pdf_text():
    """קורא את כל ה-PDFs בתיקייה"""
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
    """קורא את קובץ הלינקים ומחלץ מהם תוכן"""
    combined_text = ""
    if os.path.exists('links.txt'):
        with open('links.txt', 'r', encoding='utf-8') as f:
            links = f.readlines()
            for link in links:
                link = link.strip()
                if not link: continue
                if "youtube.com" in link or "youtu.be" in link:
                    combined_text += get_youtube_text(link)
                else:
                    combined_text += get_url_text(link)
    return combined_text

# --- 3. לוגיקה מרכזית ---

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("חסר API Key ב-Secrets!")
    st.stop()

st.title("🤖 מרכז ידע הנדסי משולב (PDF + Web + YouTube)")

# קטגוריות מורחבות מהסילבוס שלך
categories = {
    "איפיון דרישות, אימות ותיקוף (V&V)": "סכם באופן מעמיק ומפורט מאוד את עקרונות איפיון הדרישות (PRD/TRD), מודל ה-V, וההבדלים בין Verification ל-Validation.",
    "שלבי פיתוח מוצר ובדיקות": "פרט בהרחבה על שלבי PDR/CDR, תהליכי NPI, ובדיקות ATP, QTP ו-ESS כולל דוגמאות מהמקורות.",
    "ניהול סיכונים הנדסי": "סכם בצורה מפורטת את נושא ניהול הסיכונים הטכניים, ניתוח FMEA ודגמי היתכנות POD.",
    "טכנולוגיות ייצור": "פרט בהרחבה על CNC, יציקות, הזרקות פלסטיק והדפסות תלת-ממד כולל שיקולי DFM ויתרונות טכניים.",
    "סובלנויות ו-GD&T": "סכם בצורה מעמיקה ומקצועית את עקרונות ה-GD&T, צבירת טולרנסים (RSS/Worst Case) והתאמות.",
    "קורוזיה, ציפויים וטיפולי שטח": "פרט לעומק על מנגנוני קורוזיה, בחירת ציפויים, טיפולי שטח ומניעת היתפסות.",
    "תכן לאטימות (IP & EMI)": "סכם בהרחבה תכן לאטימות סביבתית IP, סיכוך אלקטרומגנטי EMI, תכן חריצים ואטמים.",
    "שיקולי תכן תרמי": "פרט לעומק על מנגנוני העברת חום, ניהול תרמי במארזים אטומים, בחירת TIM וחישובי טמפרטורת צומת.",
    "תכן כרטיסים אלקטרוניים (PCB)": "סכם בהרחבה שיקולי תכן לכרטיסים אלקטרוניים, Rigid-Flex, ומגבלות ייצור והרכבה."
}

# תפריט צד
st.sidebar.header("ניווט בידע")
category = st.sidebar.selectbox("בחר נושא לסיכום מפורט:", list(categories.keys()))

if st.sidebar.button("הפק סיכום מקיף ומפורט"):
    with st.spinner("סורק PDF, אתרים וסרטוני יוטיוב..."):
        # איסוף תוכן מכל המקורות הקבועים ב-GitHub
        pdf_content = get_pdf_text()
        links_content = get_links_content()
        all_content = pdf_content + links_content
        
        if all_content.strip():
            try:
                # שימוש ב-Gemini 3 לקבלת איכות מקסימלית
                model = genai.GenerativeModel('models/gemini-3-flash')
                
                prompt = f"""
                אתה מהנדס מכונות בכיר ומדריך טכני. 
                משימה: כתוב סיכום **ארוך מאוד, מפורט, מקצועי ומעמיק** על הנושא הבא: {category}.
                
                הנחיות לסיכום:
                1. התבסס אך ורק על המידע מהמקורות שסופקו למטה (PDF, אתרים ותמלולי יוטיוב).
                2. הסבר בהרחבה את הלוגיקה ההנדסית ("הלמה" וה"איך").
                3. חלק את התשובה לכותרות ברורות, תתי-כותרות ורשימות בולטים.
                4. אם קיימים תקנים, נוסחאות או דוגמאות במקורות - פרט אותם במלואם.
                5. אל תחסוך במילים - אני זקוק לכל המידע הזמין במקורות כדי להתכונן לראיון Senior.
                
                המקורות:
                ---
                {all_content[:200000]}
                ---
                כתוב בעברית טכנית ברמה גבוהה.
                """
                
                response = model.generate_content(prompt)
                st.header(category)
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"שגיאה בתקשורת עם המודל: {e}")
        else:
            st.warning("לא נמצא תוכן בתיקיית ה-pdfs או בקובץ links.txt.")

st.sidebar.divider()
st.sidebar.caption("המקורות נלקחים אוטומטית מתיקיית pdfs ומקובץ links.txt ב-GitHub.")

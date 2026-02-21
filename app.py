import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi

# --- 1. הגדרות דף ועיצוב CSS מתקדם ---
st.set_page_config(page_title="מרכז ידע הנדסי", layout="wide", page_icon="⚙️")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Heebo', sans-serif;
    }
    
    /* יישור לימין של אלמנטים טקסטואליים בלבד למניעת שבירת המבנה של Streamlit */
    .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, label, .stSelectbox, .stTextInput {
        direction: RTL;
        text-align: right;
    }
    
    /* העלמת כפתור הכיווץ של תפריט הצד - פותר את באג הארטיפקט החזותי */
    [data-testid="collapsedControl"] {
        display: none !important;
    }
    
    /* תיקון הרמטי לנוסחאות (KaTeX) שיישארו משמאל לימין */
    .katex, .katex-display, .katex * {
        direction: ltr !important;
        unicode-bidi: isolate !important;
    }
    .katex-display {
        text-align: center !important;
        margin: 1.5rem auto !important;
        display: block;
    }
    span.katex {
        display: inline-block;
        direction: ltr !important;
    }
    
    /* עיצוב כותרת ראשית */
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .main-header h1 {
        color: white;
        font-size: 2.8rem;
        margin: 0;
        font-weight: 700;
    }
    .main-header p {
        color: #e0e0e0;
        font-size: 1.2rem;
        margin-top: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות משיכת מידע וחיבור ---

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🚨 חסר API Key בתיקיית ה-Secrets של Streamlit!")
    st.stop()

@st.cache_resource
def get_available_models():
    """
    מושך ישירות מהשרת את רשימת המודלים שזמינים למפתח הספציפי.
    מונע שגיאות 404 על ידי שימוש בשמות המדויקים המורשים.
    """
    try:
        models = {}
        # מקבל את כל המודלים התומכים ביצירת תוכן
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                name = m.name
                # נסנן רק מודלים מתקדמים (Gemini)
                if 'gemini' in name:
                    display_name = name.split('models/')[1]
                    models[display_name] = name
        return models
    except Exception as e:
        return {}

@st.cache_data(show_spinner=False)
def get_url_text(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]): script.decompose()
        return f"\n--- תוכן מהאתר {url} ---\n" + soup.get_text()
    except: return ""

@st.cache_data(show_spinner=False)
def get_youtube_text(url):
    try:
        if "v=" in url: video_id = url.split("v=")[1].split("&")[0]
        else: video_id = url.split("/")[-1]
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['he', 'en'])
        text = " ".join([t['text'] for t in transcript])
        return f"\n--- תמלול מיוטיוב {url} ---\n" + text
    except: return ""

@st.cache_data(show_spinner=False)
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

@st.cache_data(show_spinner=False)
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

# --- 3. לוגיקה וממשק מרכזי ---

st.markdown("""
    <div class="main-header">
        <h1>⚙️ מרכז ידע הנדסי - Senior</h1>
        <p>מערכת סיכומים חכמה | הכנה לראיונות תכן מכני</p>
    </div>
""", unsafe_allow_html=True)

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

available_models = get_available_models()

with st.sidebar:
    st.header("🎛️ פאנל שליטה")
    
    if not available_models:
        st.error("🚨 לא הצלחתי למשוך מודלים מהשרת. בדוק את ה-API Key.")
        st.stop()
        
    # הצגת המודלים שבאמת זמינים בחשבון, כך שלעולם לא תהיה שגיאת 404
    selected_model_display = st.selectbox("בחר מודל עיבוד מורשה:", list(available_models.keys()))
    working_model = available_models[selected_model_display]
    
    st.divider()
    
    st.subheader("הגדרות סיכום")
    category = st.selectbox("נושא ראשי (סילבוס):", list(categories.keys()))
    focus_text = st.text_input("מיקוד ספציפי (אופציונלי):", placeholder="למשל: תתמקד בחישובי O-ring...")
    
    st.divider()
    generate_btn = st.button("🚀 הפק סיכום מקיף", type="primary", use_container_width=True)

if generate_btn:
    with st.spinner(f"מעבד נתונים בעזרת {selected_model_display}..."):
        content = get_pdf_text() + get_links_content()
        
        if content.strip():
            try:
                model = genai.GenerativeModel(working_model)
                
                if focus_text.strip():
                    task_instruction = f"משימה: הלקוח בחר בקטגוריית '{category}', אך ביקש למקד את הסיכום **אך ורק** בנושא הבא: {focus_text}. התעלם משאר נושאי הקטגוריה והרחב לעומק רק על המיקוד שביקש."
                else:
                    task_instruction = f"משימה: {categories[category]}"
                
                prompt = f"""
                אתה מהנדס מכונות בכיר ומדריך טכני.
                
                {task_instruction}
                
                הנחיות קריטיות לביצוע:
                1. התבסס אך ורק על המידע מהמקורות שסופקו.
                2. הסבר בהרחבה את הלוגיקה ההנדסית.
                3. חלק את התשובה לכותרות ורשימות בולטים.
                4. **הנחיה למשוואות:** כל נוסחה מתמטית חייבת להיכתב ב-LaTeX סטנדרטי משמאל לימין. השתמש ב- $ עבור משוואה בתוך השורה, וב- $$ למשוואה ממורכזת בשורה נפרדת.
                5. ספק תשובה ברמת Senior Mechanical Engineer.
                
                המקורות:
                ---
                {content[:250000]}
                ---
                כתוב בעברית טכנית ברמה גבוהה מאוד.
                """
                response = model.generate_content(prompt)
                
                display_title = f"📚 נושא: {category}"
                if focus_text.strip():
                    display_title += f" | מיקוד: {focus_text}"
                    
                st.subheader(display_title)
                
                with st.container(border=True):
                    st.markdown(response.text)
                    
            except Exception as e:
                st.error(f"שגיאה בהפקת התוכן: {e}")
        else:
            st.warning("לא נמצא תוכן במקורות שלך ב-GitHub (תיקיית pdfs או קובץ links.txt).")

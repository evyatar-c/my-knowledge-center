import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# --- 1. הגדרות דף ועיצוב CSS מתקדם (שומר על כל התיקונים) ---
st.set_page_config(page_title="מרכז ידע הנדסי", layout="wide", page_icon="⚙️")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Heebo', sans-serif;
    }
    
    /* יישור לימין של אלמנטים טקסטואליים בסיסיים */
    .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, label, .stSelectbox, .stTextInput {
        direction: rtl !important;
        text-align: right !important;
    }
    
    /* תיקון ייעודי לרשימות (בולטים ומספרים) */
    .stMarkdown p, .stMarkdown li {
        direction: rtl !important;
        text-align: right !important;
    }
    .stMarkdown ul, .stMarkdown ol {
        direction: rtl !important;
        padding-right: 2.5rem !important;
        padding-left: 0 !important;
        text-align: right !important;
    }
    
    /* העלמת כפתור הכיווץ של תפריט הצד - פותר את באג הארטיפקט */
    [data-testid="collapsedControl"] {
        display: none !important;
    }
    
    /* תיקון הרמטי לנוסחאות (KaTeX) */
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

# --- 2. פונקציות AI ומשיכת מידע ---

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🚨 חסר API Key בתיקיית ה-Secrets של Streamlit!")
    st.stop()

@st.cache_resource
def get_available_models():
    try:
        models = {}
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                name = m.name
                if 'gemini-3' in name.lower():
                    clean_name = name.split('models/')[1]
                    if 'pro' in clean_name:
                        models[f"🧠 {clean_name} (מעמיק, מומלץ)"] = name
                    elif 'think' in clean_name:
                        models[f"🤔 {clean_name} (הסקה וחשיבה)"] = name
                    elif 'flash' in clean_name:
                        models[f"⚡ {clean_name} (מהיר)"] = name
                    else:
                        models[clean_name] = name
        return models
    except: return {}

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
        for filename in [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]:
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

# --- 3. מנוע RAG חכם (זיכרון וחיפוש ב-RAM) ---

def chunk_text(text, chunk_size=1500, overlap=300):
    """חותך את המידע למקטעים עם חפיפה כדי לא לפספס הקשר"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def retrieve_top_chunks(query, chunks, top_k=20):
    """שולף את המקטעים הרלוונטיים ביותר מתוך הזיכרון באמצעות אלגוריתם TF-IDF"""
    if not chunks: return ""
    if len(chunks) <= top_k: return "\n...\n".join(chunks)
    
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(chunks + [query])
    cosine_similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
    
    # שליפת האינדקסים של המקטעים עם הציון הגבוה ביותר
    top_indices = cosine_similarities.argsort()[-top_k:][::-1]
    
    # סידור מחדש לפי סדר הופעה במסמך כדי לשמור על רצף קריאה הגיוני למודל
    top_indices = sorted(top_indices) 
    return "\n...\n".join([chunks[i] for i in top_indices])

# --- 4. לוגיקה וממשק מרכזי ---

st.markdown("""
    <div class="main-header">
        <h1>⚙️ מרכז ידע הנדסי - Senior</h1>
        <p>מערכת RAG חכמה מבוססת Gemini 3 | הכנה לראיונות תכן מכני</p>
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
        
    selected_model_display = st.selectbox("בחר מודל עיבוד מורשה:", list(available_models.keys()))
    working_model = available_models[selected_model_display]
    
    st.divider()
    st.subheader("הגדרות סיכום")
    category = st.selectbox("נושא ראשי (סילבוס):", list(categories.keys()))
    focus_text = st.text_input("מיקוד ספציפי (אופציונלי):", placeholder="למשל: תתמקד בחישובי O-ring...")
    
    st.divider()
    generate_btn = st.button("🚀 הפק סיכום מקיף", type="primary", use_container_width=True)

if generate_btn:
    with st.spinner(f"בונה אינדקס, מחפש מקורות ומעבד נתונים בעזרת {selected_model_display}..."):
        
        # 1. טעינת כל החומר
        raw_content = get_pdf_text() + get_links_content()
        
        if raw_content.strip():
            try:
                # 2. חיתוך החומר ושליפה חכמה של ה-20 מקטעים הרלוונטיים ביותר
                chunks = chunk_text(raw_content)
                search_query = focus_text if focus_text.strip() else category
                relevant_content = retrieve_top_chunks(search_query, chunks)
                
                # 3. הגדרת התצורה (מקסימום טוקנים פלט, טמפרטורה נמוכה לדיוק)
                generation_config = genai.types.GenerationConfig(
                    max_output_tokens=8192,
                    temperature=0.3
                )
                model = genai.GenerativeModel(working_model, generation_config=generation_config)
                
                if focus_text.strip():
                    task_instruction = f"משימה: הלקוח בחר בקטגוריית '{category}', אך ביקש למקד את הסיכום אך ורק בנושא הבא: {focus_text}. התעלם משאר נושאי הקטגוריה. ספק צלילת עומק הנדסית ומפורטת לנושא זה בלבד."
                else:
                    task_instruction = f"משימה: {categories[category]}"
                
                prompt = f"""
                אתה מהנדס מכונות בכיר ומדריך טכני. המטרה שלך היא לייצר מסמך לימוד מקיף, מעמיק ומפורט ככל האפשר.
                איסור מוחלט על תמצות: אל תשמיט שום פרט טכני, הסבר מנגנונים לעומק ואל תדלג על שלבים בתיאור.
                
                {task_instruction}
                
                הנחיות קריטיות לביצוע:
                1. התבסס אך ורק על המידע מהמקורות שסופקו למטה.
                2. הסבר בהרחבה את הלוגיקה ההנדסית ("הלמה" ו"האיך"). צלול לפרטים המיקרוסקופיים והמקרוסקופיים.
                3. חלק את התשובה לכותרות ראשיות, כותרות משנה, ורשימות בולטים ארוכות ומפורטות.
                4. **הנחיה למשוואות:** כל נוסחה מתמטית חייבת להיכתב ב-LaTeX סטנדרטי משמאל לימין. השתמש ב- $ עבור משוואה בתוך השורה, וב- $$ למשוואה ממורכזת בשורה נפרדת.
                5. ספק תשובה ארוכה מאוד ברמת Senior Mechanical Engineer.
                
                המקורות שנשלפו מהמאגר שלך:
                ---
                {relevant_content}
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
                st.error(f"שגיאה בהפקת התוכן (יתכן וחריגת מכסה אם נבחרו מודלים כבדים מדי ברצף): {e}")
        else:
            st.warning("לא נמצא תוכן במקורות שלך ב-GitHub (תיקיית pdfs או קובץ links.txt).")

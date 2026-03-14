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
import json
from streamlit_lottie import st_lottie

# --- 1. הגדרות דף ועיצוב UI/UX מתקדם ---
st.set_page_config(page_title="מרכז ידע הנדסי", layout="wide", page_icon="🚀")

# פונקציה לטעינת אנימציות Lottie
@st.cache_data
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200: return None
        return r.json()
    except: return None

# טעינת אנימציית מהנדס/טכנולוגיה
lottie_engineer = load_lottieurl("https://assets2.lottiefiles.com/packages/lf20_UJNc2t.json")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Heebo', sans-serif;
    }
    
    /* === אנימציית רקע דינמית (Moving Gradient) === */
    .stApp {
        background: linear-gradient(-45deg, #0f2027, #203a43, #2c5364, #0f2027);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
        color: white; /* התאמת טקסט לרקע כהה */
    }
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* === עיצוב זכוכית (Glassmorphism) לתפריט הצד === */
    [data-testid="stSidebar"] {
        background: rgba(15, 32, 39, 0.6) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border-left: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* === כותרת מרכזית מרחפת === */
    .glass-header {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(15px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 2rem;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        transition: transform 0.3s ease;
    }
    .glass-header:hover {
        transform: translateY(-5px);
    }
    .glass-header h1 {
        background: -webkit-linear-gradient(45deg, #4facfe, #00f2fe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 700;
        margin: 0;
    }
    .glass-header p { color: #b0c4de; font-size: 1.2rem; }

    /* === כרטיסיית התשובה (Glass Card) === */
    .stContainer {
        background: rgba(0, 0, 0, 0.4) !important;
        backdrop-filter: blur(10px);
        border-radius: 15px;
        border: 1px solid rgba(0, 242, 254, 0.3) !important;
        padding: 20px;
        box-shadow: 0 0 20px rgba(0, 242, 254, 0.1);
    }

    /* === כפתור זוהר (Neon Button) === */
    .stButton>button {
        background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%) !important;
        color: #000 !important;
        font-weight: bold !important;
        border: none !important;
        border-radius: 50px !important;
        padding: 0.75rem 2rem !important;
        box-shadow: 0 4px 15px rgba(0, 242, 254, 0.4) !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 6px 20px rgba(0, 242, 254, 0.6) !important;
    }

    /* יישור טקסט ו-RTL */
    .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, label, .stSelectbox, .stTextInput {
        direction: rtl !important;
        text-align: right !important;
        color: #e0e0e0;
    }
    .stMarkdown p, .stMarkdown li {
        direction: rtl !important;
        text-align: right !important;
        font-size: 1.1rem;
        line-height: 1.8;
    }
    .stMarkdown ul, .stMarkdown ol {
        direction: rtl !important;
        padding-right: 2.5rem !important;
        padding-left: 0 !important;
        text-align: right !important;
    }
    div[data-baseweb="select"] > div, div[data-baseweb="popover"], ul[role="listbox"], ul[role="listbox"] li, li[role="option"], div[role="option"] {
        direction: rtl !important;
        text-align: right !important;
    }
    
    /* הסתרת כפתור התפריט המעצבן */
    [data-testid="collapsedControl"] { display: none !important; }

    /* הגנה על נוסחאות LaTeX */
    .katex, .katex-display, .katex * {
        direction: ltr !important;
        unicode-bidi: isolate !important;
        color: #00f2fe; /* צבע תכלת לנוסחאות שיבלטו על הרקע הכהה */
    }
    .katex-display {
        text-align: center !important;
        margin: 1.5rem auto !important;
        display: block;
        background: rgba(0,0,0,0.3);
        padding: 10px;
        border-radius: 8px;
    }
    span.katex { display: inline-block; direction: ltr !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות AI ומשיכת מידע (כמו מקודם) ---

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
                    if 'pro' in clean_name: models[f"🧠 {clean_name} (מעמיק, מומלץ)"] = name
                    elif 'think' in clean_name: models[f"🤔 {clean_name} (הסקה וחשיבה)"] = name
                    elif 'flash' in clean_name: models[f"⚡ {clean_name} (מהיר)"] = name
                    else: models[clean_name] = name
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
                if "youtube.com" in link or "youtu.be" in link: combined_text += get_youtube_text(link)
                else: combined_text += get_url_text(link)
    return combined_text

def chunk_text(text, chunk_size=1500, overlap=300):
    chunks, start = [], 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def retrieve_top_chunks(query, chunks, top_k=20):
    if not chunks: return ""
    if len(chunks) <= top_k: return "\n...\n".join(chunks)
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(chunks + [query])
    cosine_similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
    top_indices = sorted(cosine_similarities.argsort()[-top_k:][::-1])
    return "\n...\n".join([chunks[i] for i in top_indices])

# --- 3. ממשק משתמש מרכזי ---

# כותרת מעוצבת עם אנימציה
col1, col2 = st.columns([1, 5])
with col1:
    if lottie_engineer:
        st_lottie(lottie_engineer, height=120, key="engineer")
with col2:
    st.markdown("""
        <div class="glass-header">
            <h1>מרכז ידע הנדסי - Senior</h1>
            <p>מערכת RAG חכמה מבוססת Gemini 3 | סביבת למידה אינטראקטיבית</p>
        </div>
    """, unsafe_allow_html=True)

categories_data = {
    "איפיון דרישות, אימות ותיקוף (V&V)": ["איפיון דרישות: הבחנה בין PRD ל-TRD וגזירת דרישות", "מודל ה-V: הקשר המבני בין דרישות לבדיקות", "שיטות אימות (Verification)", "תיקוף (Validation)"],
    "שלבי פיתוח מוצר ובדיקות הוכחה": ["מחזור חיי פיתוח: PDR, CDR, NPI", "בדיקות קבלה (ATP)", "בדיקות הסמכה (QTP)", "סינון סביבתי (ESS)", "בחינת מוצר ראשון FAI"],
    "ניהול סיכונים הנדסי": ["צמצום סיכונים (POD)", "טבלת ניהול סיכונים", "ניתוח FMEA"],
    "טכנולוגיות ייצור (Conventional & Advanced)": ["ייצור גורע: עיבוד שבבי ו-DFM", "יציקות מתכת", "ייצור מוסף (תלת-ממד)", "הזרקות פלסטיק", "עיצוב מתכת (Forming)"],
    "סובלנויות ו-GD&T": ["בקרות גיאומטריות", "מושג Virtual Condition ו-MMC", "ניתוח צבירת טולרנסים (Worst Case מול RSS)", "מציאת טולרנסים (Fasteners)", "התאמות (Fits)"],
    "קורוזיה, ציפויים וטיפולי שטח": ["סוגי מתכות וסגסוגות", "קורוזיה גלוונית ומאמצים", "שיקולים בבחירת ציפויים", "מניעת היתפסות (Galling)"],
    "תכן לאטימות (IP & EMI)": ["רמות IP", "תכן אטמים וחישובי דחיסה", "חריצי ניקוז ואוורור", "אטימות אלקטרומגנטית (EMI)"],
    "שיקולי תכן תרמי": ["מנגנוני מעבר חום", "משוואות חום ושרשרת נגדים", "טמפ' צומת ו-Heat Sinks"],
    "תכן פלסטיק וחומרים מתקדמים": ["תכן להזרקה (עובי דופן, חליצה)", "פולימרים הנדסיים"],
    "תכן כרטיסים אלקטרוניים (PCB)": ["מגבלות עריכה וקדחים", "גמיש קשיח", "ציפויים קונפורמיים", "שלבי ייצור והרכבה"],
    "היבטי עלות וניהול פרויקט": ["Design to Cost (DTC)", "מודלי ניהול BTP/BTS", "רכיבי מדף (COTS)", "גאנט ואבני דרך"],
    "אנליזות וחישובים הנדסיים": ["אנליזות חוזק (Von Mises)", "מאמצים בבורג", "אנליזות רעידות", "אנליזות תרמו-מכניות"],
    "תכן להרכבתיות ואמינות (DFA/DFS)": ["תכן להרכבתיות", "אמינות ותחזוקתיות (MTTR)"]
}

available_models = get_available_models()

with st.sidebar:
    st.header("🎛️ חדר בקרה")
    
    if not available_models:
        st.error("🚨 שגיאת התחברות לשרת (API Key)")
        st.stop()
        
    selected_model_display = st.selectbox("מנוע עיבוד AI:", list(available_models.keys()))
    working_model = available_models[selected_model_display]
    
    st.divider()
    
    main_category = st.selectbox("ספריית ידע (סילבוס):", list(categories_data.keys()))
    selected_sub_topic = st.selectbox("התמקדות בתת-נושא:", ["ללא"] + categories_data[main_category])
    focus_text = st.text_input("הכוונת מנוע (מלל חופשי):", placeholder="הזן דגשים ספציפיים...")
    
    st.divider()
    generate_btn = st.button("🚀 הפעל עיבוד נתונים", type="primary", use_container_width=True)

if generate_btn:
    with st.spinner(f"המודל מנתח מקורות ומפיק תובנות..."):
        raw_content = get_pdf_text() + get_links_content()
        
        if raw_content.strip():
            try:
                search_query = main_category
                if selected_sub_topic != "ללא": search_query += " " + selected_sub_topic
                if focus_text.strip(): search_query += " " + focus_text.strip()
                    
                chunks = chunk_text(raw_content)
                relevant_content = retrieve_top_chunks(search_query, chunks)
                
                task_instruction = f"הנושא הראשי: {main_category}.\n"
                if selected_sub_topic != "ללא": task_instruction += f"תת-הנושא להתמקדות: {selected_sub_topic}.\n"
                if focus_text.strip(): task_instruction += f"מיקוד ספציפי וחשוב: {focus_text}.\n"
                
                task_instruction += "ייצר מסמך לימוד מקיף ומעמיק סביב המיקוד. אל תתמצת כלל."

                generation_config = genai.types.GenerationConfig(max_output_tokens=8192, temperature=0.3)
                model = genai.GenerativeModel(working_model, generation_config=generation_config)
                
                prompt = f"""
                אתה מהנדס מכונות בכיר ומדריך טכני. 
                {task_instruction}
                
                הנחיות קריטיות לביצוע:
                1. התבסס אך ורק על המידע מהמקורות.
                2. הסבר בהרחבה את הלוגיקה ההנדסית ("הלמה" ו"האיך").
                3. חלק לכותרות ורשימות בולטים ארוכות.
                4. **משוואות:** כל נוסחה מתמטית תכתב ב-LaTeX משמאל לימין ($ עבור שורה, $$ לממורכזת).
                5. ספק תשובה ברמת Senior Mechanical Engineer.
                
                המקורות:
                ---
                {relevant_content}
                ---
                כתוב בעברית טכנית ברמה גבוהה.
                """
                response = model.generate_content(prompt)
                
                display_title = f"📚 {main_category}"
                if selected_sub_topic != "ללא": display_title += f" | {selected_sub_topic.split(':')[0]}"
                
                # הצגת התשובה בתוך "כרטיסיית זכוכית"
                with st.container(border=True):
                    st.subheader(display_title)
                    st.markdown(response.text)
                    
            except Exception as e:
                st.error(f"שגיאת תקשורת/מכסה: {e}")
        else:
            st.warning("המאגר ריק. וודא העלאת PDF או קישורים.")

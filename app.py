"""
HayMAS - AI Writing Studio
Zustandsbasiertes UI: IDLE → PRODUCING → COMPLETE
"""

import streamlit as st
import os
import sys
import glob
from datetime import datetime

sys.path.append(os.path.dirname(__file__))

from config import (
    AGENT_MODELS,
    AVAILABLE_MODELS,
    validate_api_keys,
    OUTPUT_DIR
)
from agents import (
    OrchestratorAgent,
    ResearcherAgent,
    WriterAgent,
    EditorAgent,
    EventType
)
from agents.logging import create_logger

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="HayMAS",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================================
# SESSION STATE
# ============================================================================
def init_state():
    defaults = {
        "app_state": "idle",  # idle | producing | complete
        "question": "",
        "events": [],
        "article_path": None,
        "article_content": None,
        "show_archive": False,
        "show_settings": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ============================================================================
# MINIMAL STRUCTURAL CSS
# ============================================================================
st.markdown("""
<style>
    /* Hide Streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }
    [data-testid="stSidebar"] { display: none; }
    .stDeployButton { display: none; }
    
    /* Base */
    .stApp {
        background: #fafafa;
    }
    
    .main .block-container {
        padding: 0;
        max-width: 100%;
    }
    
    /* ===== HEADER ===== */
    .studio-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 56px;
        background: #fff;
        border-bottom: 1px solid #e5e5e5;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 24px;
        z-index: 100;
    }
    
    .studio-brand {
        font-size: 16px;
        font-weight: 600;
        color: #111;
    }
    
    .studio-nav {
        display: flex;
        gap: 16px;
        font-size: 14px;
    }
    
    .studio-nav a {
        color: #666;
        text-decoration: none;
        cursor: pointer;
    }
    
    .studio-nav a:hover {
        color: #111;
    }
    
    /* ===== MAIN WORKSPACE ===== */
    .workspace {
        margin-top: 56px;
        min-height: calc(100vh - 56px);
        display: flex;
        flex-direction: column;
    }
    
    /* ===== STATE: IDLE ===== */
    .state-idle {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 48px 24px;
    }
    
    .idle-container {
        width: 100%;
        max-width: 640px;
    }
    
    .idle-title {
        font-size: 24px;
        font-weight: 600;
        color: #111;
        margin-bottom: 8px;
        text-align: center;
    }
    
    .idle-subtitle {
        font-size: 14px;
        color: #666;
        margin-bottom: 32px;
        text-align: center;
    }
    
    /* ===== STATE: PRODUCING ===== */
    .state-producing {
        flex: 1;
        display: flex;
        flex-direction: column;
        padding: 24px;
        max-width: 800px;
        margin: 0 auto;
        width: 100%;
    }
    
    .producing-header {
        margin-bottom: 24px;
    }
    
    .producing-title {
        font-size: 14px;
        font-weight: 600;
        color: #111;
        margin-bottom: 4px;
    }
    
    .producing-question {
        font-size: 13px;
        color: #666;
    }
    
    .producing-phases {
        display: flex;
        gap: 8px;
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid #e5e5e5;
    }
    
    .phase {
        font-size: 12px;
        padding: 4px 12px;
        border-radius: 4px;
        background: #f5f5f5;
        color: #999;
    }
    
    .phase.active {
        background: #111;
        color: #fff;
    }
    
    .phase.done {
        background: #e5e5e5;
        color: #666;
    }
    
    .event-list {
        flex: 1;
        overflow-y: auto;
    }
    
    .event-item {
        padding: 12px 0;
        border-bottom: 1px solid #f0f0f0;
        font-size: 13px;
    }
    
    .event-agent {
        font-weight: 600;
        color: #111;
        margin-bottom: 2px;
    }
    
    .event-content {
        color: #666;
    }
    
    /* ===== STATE: COMPLETE ===== */
    .state-complete {
        flex: 1;
        display: flex;
        flex-direction: column;
        padding: 24px;
        max-width: 800px;
        margin: 0 auto;
        width: 100%;
    }
    
    .complete-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid #e5e5e5;
    }
    
    .complete-title {
        font-size: 14px;
        font-weight: 600;
        color: #111;
    }
    
    .complete-actions {
        display: flex;
        gap: 8px;
    }
    
    .article-content {
        flex: 1;
        background: #fff;
        border: 1px solid #e5e5e5;
        border-radius: 4px;
        padding: 32px;
        overflow-y: auto;
    }
    
    /* ===== ARCHIVE PANEL ===== */
    .archive-panel {
        position: fixed;
        top: 56px;
        right: 0;
        width: 320px;
        height: calc(100vh - 56px);
        background: #fff;
        border-left: 1px solid #e5e5e5;
        padding: 24px;
        overflow-y: auto;
        z-index: 50;
    }
    
    .archive-title {
        font-size: 14px;
        font-weight: 600;
        color: #111;
        margin-bottom: 16px;
    }
    
    .archive-item {
        padding: 12px 0;
        border-bottom: 1px solid #f0f0f0;
        cursor: pointer;
    }
    
    .archive-item:hover {
        background: #fafafa;
    }
    
    .archive-item-title {
        font-size: 13px;
        color: #111;
        margin-bottom: 2px;
    }
    
    .archive-item-date {
        font-size: 11px;
        color: #999;
    }
    
    /* ===== SETTINGS PANEL ===== */
    .settings-panel {
        position: fixed;
        top: 56px;
        right: 0;
        width: 320px;
        height: calc(100vh - 56px);
        background: #fff;
        border-left: 1px solid #e5e5e5;
        padding: 24px;
        overflow-y: auto;
        z-index: 50;
    }
    
    .settings-title {
        font-size: 14px;
        font-weight: 600;
        color: #111;
        margin-bottom: 16px;
    }
    
    .settings-section {
        margin-bottom: 24px;
    }
    
    .settings-label {
        font-size: 12px;
        color: #666;
        margin-bottom: 8px;
    }
    
    /* ===== BUTTONS ===== */
    .stButton > button {
        background: #111;
        color: #fff;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 500;
    }
    
    .stButton > button:hover {
        background: #333;
    }
    
    /* Secondary buttons */
    div[data-testid="column"]:nth-child(2) .stButton > button {
        background: #fff;
        color: #111;
        border: 1px solid #e5e5e5;
    }
    
    div[data-testid="column"]:nth-child(2) .stButton > button:hover {
        background: #f5f5f5;
    }
    
    /* Text area */
    .stTextArea textarea {
        border: 1px solid #e5e5e5;
        border-radius: 4px;
        font-size: 14px;
    }
    
    .stTextArea textarea:focus {
        border-color: #111;
        box-shadow: none;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# COMPONENTS
# ============================================================================

def render_header():
    """Fixed header with brand and navigation"""
    archive_link = "javascript:void(0)" 
    settings_link = "javascript:void(0)"
    
    st.markdown(f"""
    <div class="studio-header">
        <div class="studio-brand">📚 HayMAS</div>
        <div class="studio-nav">
            <span id="archive-toggle" style="cursor:pointer;">Archiv</span>
            <span id="settings-toggle" style="cursor:pointer;">Einstellungen</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_idle():
    """IDLE state: Input form centered"""
    st.markdown('<div class="workspace"><div class="state-idle"><div class="idle-container">', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="idle-title">Wissensartikel erstellen</div>
    <div class="idle-subtitle">Beschreibe ein Thema und lass KI-Agenten einen Artikel generieren</div>
    """, unsafe_allow_html=True)
    
    question = st.text_area(
        "Thema",
        value=st.session_state.question,
        height=120,
        placeholder="z.B.: Wie funktioniert Retrieval Augmented Generation (RAG)?",
        label_visibility="collapsed"
    )
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Artikel generieren", type="primary", use_container_width=True):
            if question.strip():
                st.session_state.question = question
                st.session_state.app_state = "producing"
                st.session_state.events = []
                st.rerun()
            else:
                st.error("Bitte ein Thema eingeben")
    
    st.markdown('</div></div></div>', unsafe_allow_html=True)


def render_producing(agent_tiers: dict):
    """PRODUCING state: Show agent activity"""
    st.markdown('<div class="workspace"><div class="state-producing">', unsafe_allow_html=True)
    
    # Header with question
    st.markdown(f"""
    <div class="producing-header">
        <div class="producing-title">Artikel wird erstellt...</div>
        <div class="producing-question">{st.session_state.question[:100]}{'...' if len(st.session_state.question) > 100 else ''}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Phase indicators
    phases_html = """
    <div class="producing-phases">
        <div class="phase" id="phase-research">Recherche</div>
        <div class="phase" id="phase-structure">Struktur</div>
        <div class="phase" id="phase-writing">Schreiben</div>
        <div class="phase" id="phase-editing">Überarbeitung</div>
    </div>
    """
    st.markdown(phases_html, unsafe_allow_html=True)
    
    # Progress and controls
    progress_bar = st.progress(0)
    status_placeholder = st.empty()
    
    col1, col2 = st.columns([3, 1])
    with col2:
        stop_btn = st.button("Abbrechen", key="stop_btn")
    
    # Event display
    event_container = st.container()
    
    # Process
    try:
        logger = create_logger(st.session_state.question)
        
        orchestrator = OrchestratorAgent(tier=agent_tiers.get("orchestrator", "premium"))
        researcher = ResearcherAgent(tier=agent_tiers.get("researcher", "premium"))
        writer = WriterAgent(tier=agent_tiers.get("writer", "premium"))
        editor = EditorAgent(tier=agent_tiers.get("editor", "premium"))
        
        orchestrator.set_agents(researcher, writer, editor)
        
        event_count = 0
        for event in orchestrator.process_article(st.session_state.question):
            if stop_btn:
                st.session_state.app_state = "idle"
                st.rerun()
                break
            
            event_count += 1
            st.session_state.events.append(event)
            logger.log_event(event.agent_name, event.event_type.value, event.content, event.data)
            
            progress = min(event_count / 30, 0.95)
            progress_bar.progress(progress)
            status_placeholder.text(f"{event.agent_name}")
            
            with event_container:
                content = event.content[:200] + '...' if len(event.content) > 200 else event.content
                st.markdown(f"""
                <div class="event-item">
                    <div class="event-agent">{event.agent_name}</div>
                    <div class="event-content">{content}</div>
                </div>
                """, unsafe_allow_html=True)
        
        progress_bar.progress(1.0)
        logger.save()
        
        # Get result
        if st.session_state.events:
            last_event = st.session_state.events[-1]
            if hasattr(last_event, 'data') and last_event.data.get('article_path'):
                article_path = last_event.data['article_path']
                if os.path.exists(article_path):
                    with open(article_path, "r", encoding="utf-8") as f:
                        st.session_state.article_content = f.read()
                    st.session_state.article_path = article_path
        
        st.session_state.app_state = "complete"
        st.rerun()
        
    except Exception as e:
        st.error(f"Fehler: {str(e)}")
        st.session_state.app_state = "idle"
    
    st.markdown('</div></div>', unsafe_allow_html=True)


def render_complete():
    """COMPLETE state: Show finished article"""
    st.markdown('<div class="workspace"><div class="state-complete">', unsafe_allow_html=True)
    
    # Header with actions
    st.markdown("""
    <div class="complete-header">
        <div class="complete-title">Artikel fertig</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("Neuer Artikel", type="primary"):
            st.session_state.app_state = "idle"
            st.session_state.question = ""
            st.session_state.article_content = None
            st.session_state.article_path = None
            st.rerun()
    with col2:
        if st.session_state.article_content:
            st.download_button(
                "Herunterladen",
                data=st.session_state.article_content,
                file_name=os.path.basename(st.session_state.article_path) if st.session_state.article_path else "artikel.md",
                mime="text/markdown"
            )
    
    # Article content
    st.markdown('<div class="article-content">', unsafe_allow_html=True)
    if st.session_state.article_content:
        st.markdown(st.session_state.article_content)
    else:
        st.warning("Kein Artikelinhalt verfügbar")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div></div>', unsafe_allow_html=True)


def render_archive_panel():
    """Side panel showing previous articles"""
    st.markdown('<div class="archive-panel">', unsafe_allow_html=True)
    st.markdown('<div class="archive-title">Archiv</div>', unsafe_allow_html=True)
    
    articles = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.md")), key=os.path.getmtime, reverse=True)
    
    if not articles:
        st.markdown('<p style="color:#999;font-size:13px;">Noch keine Artikel</p>', unsafe_allow_html=True)
    else:
        for article_path in articles[:10]:
            filename = os.path.basename(article_path)
            stat = os.stat(article_path)
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y")
            
            display_name = filename.replace(".md", "").replace("_", " ")[:40]
            
            if st.button(f"{display_name}", key=f"arch_{filename}"):
                with open(article_path, "r", encoding="utf-8") as f:
                    st.session_state.article_content = f.read()
                st.session_state.article_path = article_path
                st.session_state.app_state = "complete"
                st.session_state.show_archive = False
                st.rerun()
    
    if st.button("Schließen", key="close_archive"):
        st.session_state.show_archive = False
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_settings_panel(agent_tiers: dict):
    """Side panel for model configuration"""
    st.markdown('<div class="settings-panel">', unsafe_allow_html=True)
    st.markdown('<div class="settings-title">Einstellungen</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="settings-section">', unsafe_allow_html=True)
    st.markdown('<div class="settings-label">Modell-Konfiguration</div>', unsafe_allow_html=True)
    
    for agent_name, agent_config in AGENT_MODELS.items():
        tier = st.radio(
            agent_name.capitalize(),
            options=["premium", "budget"],
            format_func=lambda x: "Premium" if x == "premium" else "Budget",
            key=f"tier_{agent_name}",
            horizontal=True
        )
        agent_tiers[agent_name] = tier
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # API Status
    st.markdown('<div class="settings-section">', unsafe_allow_html=True)
    st.markdown('<div class="settings-label">API Status</div>', unsafe_allow_html=True)
    api_status = validate_api_keys()
    for provider, status in api_status.items():
        icon = "✓" if status else "✗"
        st.markdown(f"{icon} {provider.upper()}", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("Schließen", key="close_settings"):
        st.session_state.show_settings = False
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================================
# MAIN
# ============================================================================
def main():
    render_header()
    
    # Navigation toggles (via query params as Streamlit workaround)
    col_hidden = st.columns([1])[0]
    with col_hidden:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📁", key="toggle_archive", help="Archiv"):
                st.session_state.show_archive = not st.session_state.show_archive
                st.session_state.show_settings = False
                st.rerun()
        with c2:
            if st.button("⚙️", key="toggle_settings", help="Einstellungen"):
                st.session_state.show_settings = not st.session_state.show_settings
                st.session_state.show_archive = False
                st.rerun()
    
    # Agent tiers storage
    agent_tiers = {}
    
    # Side panels
    if st.session_state.show_archive:
        render_archive_panel()
    
    if st.session_state.show_settings:
        render_settings_panel(agent_tiers)
    
    # Main state router
    if st.session_state.app_state == "idle":
        render_idle()
    elif st.session_state.app_state == "producing":
        render_producing(agent_tiers)
    elif st.session_state.app_state == "complete":
        render_complete()
    else:
        render_idle()


if __name__ == "__main__":
    main()

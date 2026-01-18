"""
HayMAS API Server
FastAPI Server für das React Frontend mit intelligenter Themenanalyse
"""

import os
import sys
import json
import glob
import io
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from fpdf import FPDF

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
)
from agents.orchestrator import ResearchPlan, ResearchRound
from session_logger import get_log_for_article, list_all_logs, LOGS_DIR
from mcp_server.server import get_mcp_server

app = FastAPI(title="HayMAS API")


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "name": "HayMAS API",
        "frontend": "http://localhost:5173",
        "docs": "http://localhost:8000/docs",
        "endpoints": ["/api/status", "/api/models", "/api/articles", "/api/analyze", "/api/generate"]
    }


# CORS für lokale Entwicklung
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ResearchRoundModel(BaseModel):
    name: str
    focus: str
    search_query: str
    tool: str = "tavily"  # NEU: Tool für diese Runde
    enabled: bool = True


class ResearchPlanModel(BaseModel):
    topic_type: str = "general"
    time_relevance: str = "timeless"
    needs_current_data: bool = True
    geographic_focus: str = "global"
    complexity: str = "medium"
    rounds: List[ResearchRoundModel]
    use_editor: bool = False
    reasoning: str = ""
    model_recommendations: Optional[dict] = None  # NEU: Modell-Empfehlungen


class AnalyzeRequest(BaseModel):
    question: str


class GenerateRequest(BaseModel):
    question: str
    tiers: Optional[dict] = None
    plan: Optional[ResearchPlanModel] = None  # NEU: Optionaler benutzerdefinierter Plan
    # Legacy-Parameter (werden ignoriert wenn plan gegeben)
    research_rounds: Optional[int] = None
    use_editor: Optional[bool] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/api/status")
def get_status():
    """API Key Status"""
    return validate_api_keys()


@app.get("/api/models")
def get_models():
    """Verfügbare Modelle und Agents"""
    agents = {}
    for name, config in AGENT_MODELS.items():
        agents[name] = {
            "description": config.description,
            "premium": {
                "key": config.premium,
                "name": AVAILABLE_MODELS[config.premium].name,
                "provider": AVAILABLE_MODELS[config.premium].provider
            },
            "budget": {
                "key": config.budget,
                "name": AVAILABLE_MODELS[config.budget].name,
                "provider": AVAILABLE_MODELS[config.budget].provider
            }
        }
    return {"agents": agents}


@app.get("/api/tools")
def get_tools():
    """
    Verfügbare Research-Tools.
    
    Returns:
        Liste aller Research-Tools mit Metadaten für Frontend.
    """
    mcp = get_mcp_server()
    return {"tools": mcp.get_research_tools_info()}


@app.get("/api/tools/{topic_type}")
def get_tools_for_topic(topic_type: str):
    """
    Empfohlene Tools für einen Thementyp.
    
    Args:
        topic_type: z.B. "tech", "science", "business", "current_events"
    
    Returns:
        Liste empfohlener Tool-IDs
    """
    mcp = get_mcp_server()
    return {"topic_type": topic_type, "recommended_tools": mcp.get_research_tools_for_topic(topic_type)}


@app.get("/api/articles")
def get_articles():
    """Liste aller Artikel"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    articles = []
    
    for filepath in sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.md")), key=os.path.getmtime, reverse=True):
        stat = os.stat(filepath)
        filename = os.path.basename(filepath)
        
        # Ersten Titel aus dem Artikel lesen
        title = filename
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if first_line.startswith("# "):
                    title = first_line[2:]
        except:
            pass
        
        articles.append({
            "filename": filename,
            "title": title,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "size": stat.st_size
        })
    
    return {"articles": articles}


@app.get("/api/articles/{filename}")
def get_article(filename: str):
    """Einzelner Artikel"""
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden")
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    return {"filename": filename, "content": content}


@app.get("/api/articles/{filename}/log")
def get_article_log(filename: str):
    """Log für einen bestimmten Artikel abrufen"""
    log = get_log_for_article(filename)
    
    if not log:
        raise HTTPException(status_code=404, detail="Log nicht gefunden")
    
    return log


class MarkdownPDF(FPDF):
    """PDF-Generator mit Markdown-Unterstützung."""
    
    LEFT_MARGIN = 10
    RIGHT_MARGIN = 10
    TEXT_WIDTH = 190  # A4 = 210mm - 2*10mm margins
    
    def __init__(self):
        super().__init__()
        self.set_margins(self.LEFT_MARGIN, 15, self.RIGHT_MARGIN)
        self.add_page()
        self.set_auto_page_break(auto=True, margin=25)
        
    def header(self):
        pass
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 9)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Seite {self.page_no()}', align='C')
    
    def _reset_x(self):
        """X-Position auf linken Rand zuruecksetzen."""
        self.set_x(self.LEFT_MARGIN)
        
    def render_markdown(self, md_text: str):
        """Markdown-Text zu PDF rendern."""
        lines = md_text.split('\n')
        in_code_block = False
        
        for line in lines:
            stripped = line.strip()
            self._reset_x()  # Immer X zuruecksetzen
            
            # Code-Block Start/Ende
            if stripped.startswith('```'):
                in_code_block = not in_code_block
                if in_code_block:
                    self.ln(3)
                continue
                
            # Code-Block Inhalt
            if in_code_block:
                self.set_font('Courier', '', 8)
                self.set_fill_color(245, 245, 245)
                clean_line = self._clean_text(line) if line.strip() else ' '
                self.multi_cell(self.TEXT_WIDTH, 4, clean_line, fill=True)
                continue
            
            # Leere Zeilen
            if not stripped:
                self.ln(3)
                continue
                
            # H1
            if stripped.startswith('# '):
                self.ln(5)
                self.set_font('Helvetica', 'B', 18)
                self.set_text_color(17, 17, 17)
                text = self._clean_text(stripped[2:])
                self.multi_cell(self.TEXT_WIDTH, 9, text)
                self.set_draw_color(51, 51, 51)
                self.line(self.LEFT_MARGIN, self.get_y(), self.LEFT_MARGIN + self.TEXT_WIDTH, self.get_y())
                self.ln(5)
                continue
                
            # H2
            if stripped.startswith('## '):
                self.ln(6)
                self.set_font('Helvetica', 'B', 14)
                self.set_text_color(34, 34, 34)
                text = self._clean_text(stripped[3:])
                self.multi_cell(self.TEXT_WIDTH, 7, text)
                self.ln(2)
                continue
                
            # H3
            if stripped.startswith('### '):
                self.ln(4)
                self.set_font('Helvetica', 'B', 12)
                self.set_text_color(51, 51, 51)
                text = self._clean_text(stripped[4:])
                self.multi_cell(self.TEXT_WIDTH, 6, text)
                self.ln(2)
                continue
                
            # H4
            if stripped.startswith('#### '):
                self.ln(3)
                self.set_font('Helvetica', 'B', 11)
                self.set_text_color(68, 68, 68)
                text = self._clean_text(stripped[5:])
                self.multi_cell(self.TEXT_WIDTH, 5, text)
                self.ln(1)
                continue
                
            # Horizontale Linie
            if stripped in ['---', '***', '___']:
                self.ln(5)
                self.set_draw_color(200, 200, 200)
                self.line(self.LEFT_MARGIN, self.get_y(), self.LEFT_MARGIN + self.TEXT_WIDTH, self.get_y())
                self.ln(5)
                continue
                
            # Ungeordnete Liste
            if stripped.startswith('- ') or stripped.startswith('* '):
                self.set_font('Helvetica', '', 10)
                self.set_text_color(64, 64, 64)
                text = self._clean_text(stripped[2:])
                self.cell(8, 5, '-')
                self.multi_cell(self.TEXT_WIDTH - 8, 5, text)
                continue
                
            # Geordnete Liste (1. 2. etc.)
            if len(stripped) > 2 and stripped[0].isdigit() and '.' in stripped[:4]:
                self.set_font('Helvetica', '', 10)
                self.set_text_color(64, 64, 64)
                dot_pos = stripped.find('.')
                num = stripped[:dot_pos]
                text = self._clean_text(stripped[dot_pos+1:].strip())
                self.cell(10, 5, f"{num}.")
                self.multi_cell(self.TEXT_WIDTH - 10, 5, text)
                continue
                
            # Blockquote
            if stripped.startswith('>'):
                self.set_font('Helvetica', 'I', 10)
                self.set_text_color(85, 85, 85)
                text = self._clean_text(stripped[1:].strip())
                self.cell(5, 5, '|')
                self.multi_cell(self.TEXT_WIDTH - 5, 5, text)
                continue
                
            # Normaler Paragraph
            self.set_font('Helvetica', '', 10)
            self.set_text_color(26, 26, 26)
            text = self._clean_text(stripped)
            if text:  # Nur wenn Text vorhanden
                self.multi_cell(self.TEXT_WIDTH, 5, text)
            
    def _clean_text(self, text: str) -> str:
        """Markdown-Formatierung entfernen und Text ASCII-kompatibel machen."""
        import re
        import unicodedata
        
        # Bold und Italic entfernen
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        # Inline Code
        text = re.sub(r'`(.+?)`', r'\1', text)
        # Links: [text](url) -> text
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
        
        # Alle Arten von Anführungszeichen normalisieren
        text = re.sub(r'[""„‟«»\u201c\u201d\u201e\u201f\u00ab\u00bb]', '"', text)
        text = re.sub(r'[''‚‛\u2018\u2019\u201a\u201b]', "'", text)
        
        # Striche normalisieren
        text = re.sub(r'[–—‒―\u2013\u2014\u2012\u2015]', '-', text)
        
        # Punkte und Bullets
        text = re.sub(r'[…\u2026]', '...', text)
        text = re.sub(r'[•·●○■□▪▫★☆\u2022\u00b7\u25cf\u25cb\u25a0\u25a1]', '-', text)
        
        # Pfeile
        text = re.sub(r'[→⇒➔➜►\u2192\u21d2]', '->', text)
        text = re.sub(r'[←⇐◄\u2190\u21d0]', '<-', text)
        
        # Häkchen
        text = re.sub(r'[✓✔☑\u2713\u2714]', '[x]', text)
        text = re.sub(r'[✗✘☐\u2717\u2718]', '[ ]', text)
        
        # Mathematische Symbole
        text = text.replace('×', 'x')
        text = text.replace('÷', '/')
        text = text.replace('±', '+/-')
        text = text.replace('≈', '~')
        text = text.replace('≠', '!=')
        text = text.replace('≤', '<=')
        text = text.replace('≥', '>=')
        text = text.replace('∞', 'oo')
        
        # Symbole
        text = text.replace('™', '(TM)')
        text = text.replace('®', '(R)')
        text = text.replace('©', '(c)')
        text = text.replace('€', 'EUR')
        text = text.replace('°', ' Grad')
        
        # Unicode-Normalisierung (NFKD zerlegt Zeichen)
        text = unicodedata.normalize('NFKD', text)
        
        # Nur ASCII-Zeichen behalten + deutsche Umlaute manuell ersetzen
        result = []
        for char in text:
            if ord(char) < 128:
                result.append(char)
            elif char in 'äöüÄÖÜß':
                # Umlaute durch Umschreibungen ersetzen
                umlaut_map = {'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 
                             'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue', 'ß': 'ss'}
                result.append(umlaut_map[char])
            elif char in 'éèêëáàâãåæçíìîïñóòôõøúùûýÿ':
                # Akzentbuchstaben vereinfachen
                accent_map = {'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
                             'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'å': 'a', 'æ': 'ae',
                             'ç': 'c', 'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
                             'ñ': 'n', 'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ø': 'o',
                             'ú': 'u', 'ù': 'u', 'û': 'u', 'ý': 'y', 'ÿ': 'y'}
                result.append(accent_map.get(char, ''))
            elif char in 'ÉÈÊËÁÀÂÃÅÆÇÍÌÎÏÑÓÒÔÕØÚÙÛÝ':
                accent_map = {'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
                             'Á': 'A', 'À': 'A', 'Â': 'A', 'Ã': 'A', 'Å': 'A', 'Æ': 'AE',
                             'Ç': 'C', 'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
                             'Ñ': 'N', 'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Õ': 'O', 'Ø': 'O',
                             'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ý': 'Y'}
                result.append(accent_map.get(char, ''))
            # Andere Zeichen ignorieren
        
        return ''.join(result)


@app.get("/api/articles/{filename}/pdf")
def get_article_pdf(filename: str):
    """
    Artikel als PDF herunterladen.
    
    Konvertiert die Markdown-Datei direkt zu PDF.
    """
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden")
    
    # Markdown laden
    with open(filepath, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    # PDF generieren
    pdf = MarkdownPDF()
    pdf.render_markdown(md_content)
    
    # PDF in BytesIO schreiben
    pdf_buffer = io.BytesIO()
    pdf_output = pdf.output()
    pdf_buffer.write(pdf_output)
    pdf_buffer.seek(0)
    
    # PDF-Dateiname
    pdf_filename = filename.replace('.md', '.pdf')
    
    return Response(
        content=pdf_buffer.read(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{pdf_filename}"'
        }
    )


@app.get("/api/logs")
def get_logs():
    """Liste aller Logs"""
    return {"logs": list_all_logs()}


@app.get("/api/logs/{log_filename}")
def get_log(log_filename: str):
    """Einzelnes Log abrufen"""
    filepath = os.path.join(LOGS_DIR, log_filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Log nicht gefunden")
    
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


@app.post("/api/analyze")
def analyze_topic(request: AnalyzeRequest):
    """
    Analysiert ein Thema und gibt einen empfohlenen Recherche-Plan zurück.
    
    Der User kann diesen Plan dann anpassen bevor er /api/generate aufruft.
    """
    tiers = {}  # Für Analyse verwenden wir Default-Tiers
    
    try:
        # Orchestrator erstellen für Analyse
        orchestrator = OrchestratorAgent(tier="premium")
        
        # Themenanalyse durchführen
        plan = None
        events = []
        
        for event in orchestrator.analyze_topic(request.question):
            events.append({
                "type": event.event_type.value,
                "agent": event.agent_name,
                "content": event.content
            })
            
            # Plan aus Event-Daten extrahieren
            if event.data and event.data.get("plan"):
                plan = event.data["plan"]
        
        if plan:
            return {
                "success": True,
                "plan": plan,
                "events": events
            }
        else:
            raise HTTPException(status_code=500, detail="Themenanalyse fehlgeschlagen")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analyse-Fehler: {str(e)}")


@app.post("/api/generate")
def generate_article(request: GenerateRequest):
    """
    Artikel generieren mit Server-Sent Events.
    
    Unterstützt drei Modi:
    1. Auto-Modus: Keine plan/research_rounds → Orchestrator analysiert selbst
    2. Plan-Modus: plan gegeben → Verwendet den benutzerdefinierten Plan
    3. Legacy-Modus: research_rounds gegeben → Verwendet Standard-Templates
    """
    
    tiers = request.tiers or {}
    
    def event_stream():
        try:
            # Agents erstellen
            orchestrator = OrchestratorAgent(tier=tiers.get("orchestrator", "premium"))
            researcher = ResearcherAgent(tier=tiers.get("researcher", "premium"))
            writer = WriterAgent(tier=tiers.get("writer", "premium"))
            editor = EditorAgent(tier=tiers.get("editor", "premium"))
            
            orchestrator.set_agents(researcher, writer, editor)
            
            # Plan konvertieren falls gegeben
            research_plan = None
            if request.plan:
                research_plan = ResearchPlan(
                    topic_type=request.plan.topic_type,
                    time_relevance=request.plan.time_relevance,
                    needs_current_data=request.plan.needs_current_data,
                    geographic_focus=request.plan.geographic_focus,
                    complexity=request.plan.complexity,
                    rounds=[
                        ResearchRound(
                            name=r.name,
                            focus=r.focus,
                            search_query=r.search_query,
                            tool=r.tool,  # NEU: Tool pro Runde
                            enabled=r.enabled
                        )
                        for r in request.plan.rounds
                    ],
                    use_editor=request.plan.use_editor,
                    reasoning=request.plan.reasoning,
                    model_recommendations=request.plan.model_recommendations or {}  # NEU
                )
            
            # Generierung starten
            for event in orchestrator.process_article(
                core_question=request.question,
                plan=research_plan,
                research_rounds=request.research_rounds,
                use_editor=request.use_editor,
                tiers=tiers
            ):
                event_data = {
                    "type": event.event_type.value,
                    "agent": event.agent_name,
                    "content": event.content,
                    "data": event.data
                }
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            error_data = {
                "type": "error",
                "agent": "system",
                "content": str(e),
                "data": {}
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

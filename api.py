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
from fastapi.responses import StreamingResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import markdown
from pathlib import Path
# WeasyPrint wird lazy importiert wegen macOS Library-Pfad-Problemen

sys.path.append(os.path.dirname(__file__))

from config import (
    AGENT_MODELS,
    AVAILABLE_MODELS,
    validate_api_keys,
    OUTPUT_DIR,
    reload_api_keys,
    get_api_keys_masked,
    save_api_keys,
)
from agents import (
    OrchestratorAgent,
    ResearcherAgent,
    WriterAgent,
    EditorAgent,
)
from agents.orchestrator import ResearchPlan, ResearchRound
from agents.prompt_optimizer import PromptOptimizerAgent
from session_logger import get_log_for_article, list_all_logs, LOGS_DIR
from mcp_server.server import get_mcp_server

app = FastAPI(title="HayMAS API")


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


class RefinePromptRequest(BaseModel):
    """Request für Prompt-Optimierung"""
    question: str
    format: Optional[str] = None  # "overview" | "article" | "report" | "deep_dive"
    audience: Optional[str] = None  # "experts" | "management" | "general"
    use_ai: bool = False  # True = LLM-basierte Optimierung, False = regelbasiert


class GenerateRequest(BaseModel):
    question: str
    tiers: Optional[dict] = None
    plan: Optional[ResearchPlanModel] = None  # NEU: Optionaler benutzerdefinierter Plan
    # Legacy-Parameter (werden ignoriert wenn plan gegeben)
    research_rounds: Optional[int] = None
    use_editor: Optional[bool] = None
    # NEU: Modus-Auswahl
    # "standard" = alter Flow (Recherche zuerst)
    # "deep" = Deep Thinking (LLM-Wissen zuerst) - DEPRECATED
    # "evidence" = Evidence-Gated (Claim-basiert) - EMPFOHLEN!
    mode: Optional[str] = "evidence"
    # NEU: Format/Länge des Artikels
    # "overview" = Kompakte Übersicht (3-5 Seiten)
    # "article" = Standard-Artikel (6-10 Seiten)
    # "report" = Umfassender Report (10-15 Seiten) - DEFAULT
    # "deep_dive" = Deep-Dive Analyse (15-20 Seiten)
    format: Optional[str] = "report"


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/api/status")
def get_status():
    """API Key Status"""
    return validate_api_keys()


# ============================================================================
# SETTINGS / API KEYS
# ============================================================================

class ApiKeysRequest(BaseModel):
    """Request zum Speichern von API Keys."""
    anthropic: Optional[str] = None
    openai: Optional[str] = None
    gemini: Optional[str] = None
    tavily: Optional[str] = None


@app.get("/api/settings")
def get_settings():
    """
    Gibt die aktuellen Einstellungen zurück.
    API Keys werden maskiert angezeigt.
    """
    return {
        "api_keys": get_api_keys_masked(),
        "api_status": validate_api_keys(),
    }


@app.post("/api/settings/keys")
def save_settings_keys(request: ApiKeysRequest):
    """
    Speichert API Keys in der persistenten Konfiguration.
    Leere Werte werden ignoriert (behalten den vorherigen Key).
    """
    keys_to_save = {}
    if request.anthropic:
        keys_to_save["anthropic"] = request.anthropic
    if request.openai:
        keys_to_save["openai"] = request.openai
    if request.gemini:
        keys_to_save["gemini"] = request.gemini
    if request.tavily:
        keys_to_save["tavily"] = request.tavily
    
    if keys_to_save:
        save_api_keys(keys_to_save)
    
    # Reload und Status zurückgeben
    reload_api_keys()
    
    return {
        "success": True,
        "api_keys": get_api_keys_masked(),
        "api_status": validate_api_keys(),
    }


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


@app.delete("/api/articles/{filename}")
def delete_article(filename: str):
    """
    Löscht einen Artikel aus dem Archiv.
    """
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden")
    
    try:
        os.remove(filepath)
        return {"success": True, "message": f"Artikel '{filename}' gelöscht"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Löschen fehlgeschlagen: {str(e)}")


@app.get("/api/articles/{filename}/download")
def download_article(filename: str):
    """
    Artikel als Markdown-Datei herunterladen.
    Triggert Browser-Download-Dialog.
    """
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden")
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    return Response(
        content=content.encode("utf-8"),
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@app.get("/api/articles/{filename}/log")
def get_article_log(filename: str):
    """Log für einen bestimmten Artikel abrufen"""
    log = get_log_for_article(filename)
    
    if not log:
        raise HTTPException(status_code=404, detail="Log nicht gefunden")
    
    return log


# =============================================================================
# PDF Generation - WeasyPrint with FPDF Fallback
# =============================================================================

import re
from fpdf import FPDF

# Path to CSS template
PDF_TEMPLATE_DIR = Path(__file__).parent / "templates"
PDF_CSS_PATH = PDF_TEMPLATE_DIR / "pdf_style.css"

# German month names
GERMAN_MONTHS = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember"
}


def _wrap_executive_summary(md_content: str) -> str:
    """Wrappe die Executive Summary in einen Container für besseres Styling."""
    # Finde Executive Summary Sektion
    pattern = r'(## Executive Summary\s*\n)(.*?)((?=\n---|\n## ))'
    
    def wrapper(match):
        header = match.group(1)
        content = match.group(2)
        # Füge HTML-Kommentare ein die später zu div werden
        return f'{header}<div class="executive-summary">\n\n{content}\n\n</div>\n'
    
    return re.sub(pattern, wrapper, md_content, flags=re.DOTALL | re.IGNORECASE)


def _format_literaturverzeichnis(md_content: str) -> str:
    """Formatiere das Literaturverzeichnis - jede Referenz als eigener Absatz mit korrekten Links."""
    # Finde Literaturverzeichnis Sektion
    pattern = r'(## Literaturverzeichnis\s*\n)(.*?)$'
    
    def format_reference(line: str) -> str:
        """Formatiere eine einzelne Referenz-Zeile mit korrektem Markdown-Link."""
        # Finde URL in der Zeile (http:// oder https://)
        url_pattern = r'(https?://[^\s]+)'
        
        def make_link(match):
            url = match.group(1)
            # Entferne trailing Punkt oder Komma falls vorhanden
            clean_url = url.rstrip('.,;:')
            trailing = url[len(clean_url):]
            return f'<{clean_url}>{trailing}'
        
        # Ersetze URLs durch explizite Markdown-Links mit angle brackets
        return re.sub(url_pattern, make_link, line)
    
    def formatter(match):
        header = match.group(1)
        content = match.group(2)
        
        # Jede Zeile die mit [Zahl] beginnt als eigenen Absatz
        lines = content.split('\n')
        formatted_lines = []
        for line in lines:
            line = line.strip()
            if line and re.match(r'^\[\d+\]', line):
                # Referenz-Zeile - URL korrekt formatieren und als eigenen Absatz
                formatted_line = format_reference(line)
                formatted_lines.append(f'\n{formatted_line}\n')
            elif line:
                formatted_lines.append(line)
        
        return f'{header}\n' + '\n'.join(formatted_lines)
    
    return re.sub(pattern, formatter, md_content, flags=re.DOTALL | re.IGNORECASE)


def _try_weasyprint_pdf(md_content: str, title: str) -> Optional[bytes]:
    """Versuche PDF mit WeasyPrint zu generieren (beste Qualität)."""
    try:
        from weasyprint import HTML, CSS
        
        # Sektionen wrappen/formatieren für besseres Styling
        md_content = _wrap_executive_summary(md_content)
        md_content = _format_literaturverzeichnis(md_content)
        
        # Markdown zu HTML
        md_converter = markdown.Markdown(
            extensions=['tables', 'fenced_code', 'toc', 'smarty', 'md_in_html']
        )
        html_body = md_converter.convert(md_content)
        
        now = datetime.now()
        current_date = f"{now.day}. {GERMAN_MONTHS[now.month]} {now.year}"
        
        html_content = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
</head>
<body>
    {html_body}
    <div class="document-footer">
        <p>Generiert am {current_date}</p>
        <p class="tagline"><strong>HayMAS</strong> — Dr. Hayward's AI Agent Army</p>
    </div>
</body>
</html>"""
        
        css = CSS(filename=str(PDF_CSS_PATH)) if PDF_CSS_PATH.exists() else None
        html_doc = HTML(string=html_content)
        
        return html_doc.write_pdf(stylesheets=[css] if css else None)
    except (OSError, ImportError):
        return None


class EnhancedPDF(FPDF):
    """Verbesserter PDF-Generator mit Tabellen-Support."""
    
    def __init__(self):
        super().__init__()
        self.set_margins(20, 20, 20)
        self.add_page()
        self.set_auto_page_break(auto=True, margin=25)
        self.set_font('Helvetica', '', 10)
        
    def header(self):
        if self.page_no() > 1:
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(128)
            self.cell(0, 10, 'HayMAS', align='R')
            self.ln(5)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Seite {self.page_no()}', align='C')
    
    def render_table(self, rows: List[List[str]]):
        """Rendert eine Markdown-Tabelle."""
        if not rows:
            return
            
        # Spaltenbreiten berechnen
        num_cols = len(rows[0])
        col_width = 170 / num_cols  # 210mm - 2*20mm margins
        
        self.set_font('Helvetica', '', 9)
        
        for i, row in enumerate(rows):
            # Header-Zeile
            if i == 0:
                self.set_fill_color(240, 240, 240)
                self.set_font('Helvetica', 'B', 9)
            else:
                self.set_fill_color(255, 255, 255)
                self.set_font('Helvetica', '', 9)
            
            # Zeilenhöhe basierend auf Inhalt
            max_lines = 1
            for cell in row:
                lines = len(self._clean_text(cell)) / (col_width / 2)
                max_lines = max(max_lines, int(lines) + 1)
            
            row_height = max(6, max_lines * 5)
            
            for j, cell in enumerate(row):
                x_before = self.get_x()
                self.set_draw_color(200, 200, 200)
                self.multi_cell(col_width, row_height / max_lines, 
                               self._clean_text(cell), border=1, 
                               fill=(i == 0), new_x='RIGHT', new_y='TOP')
                if j < num_cols - 1:
                    self.set_xy(x_before + col_width, self.get_y() - row_height / max_lines * max_lines)
            
            self.ln(row_height)
        
        self.ln(5)
    
    def render_markdown(self, md_text: str):
        """Markdown zu PDF rendern mit Tabellen-Support."""
        lines = md_text.split('\n')
        in_code_block = False
        table_rows = []
        in_table = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Tabellen-Erkennung
            if '|' in stripped and not in_code_block:
                # Separator-Zeile (|---|---|)
                if re.match(r'^[\|\s\-:]+$', stripped):
                    i += 1
                    continue
                
                # Tabellen-Zeile
                cells = [c.strip() for c in stripped.split('|')]
                cells = [c for c in cells if c]  # Leere Zellen am Rand entfernen
                
                if cells:
                    if not in_table:
                        in_table = True
                        table_rows = []
                    table_rows.append(cells)
                    i += 1
                    continue
            elif in_table:
                # Tabelle beenden und rendern
                self.render_table(table_rows)
                table_rows = []
                in_table = False
            
            # Code-Block
            if stripped.startswith('```'):
                in_code_block = not in_code_block
                if in_code_block:
                    self.ln(3)
                i += 1
                continue
                
            if in_code_block:
                self.set_font('Courier', '', 8)
                self.set_fill_color(245, 245, 245)
                self.multi_cell(170, 4, self._clean_text(line) or ' ', fill=True)
                i += 1
                continue
            
            # Leere Zeilen
            if not stripped:
                self.ln(3)
                i += 1
                continue
            
            # Überschriften
            if stripped.startswith('# '):
                self.ln(5)
                self.set_font('Helvetica', 'B', 16)
                self.set_text_color(17, 17, 17)
                self.multi_cell(170, 8, self._clean_text(stripped[2:]))
                self.set_draw_color(51, 51, 51)
                self.line(20, self.get_y(), 190, self.get_y())
                self.ln(5)
                i += 1
                continue
                
            if stripped.startswith('## '):
                self.ln(6)
                self.set_font('Helvetica', 'B', 13)
                self.set_text_color(34, 34, 34)
                self.multi_cell(170, 7, self._clean_text(stripped[3:]))
                self.ln(2)
                i += 1
                continue
                
            if stripped.startswith('### '):
                self.ln(4)
                self.set_font('Helvetica', 'B', 11)
                self.set_text_color(51, 51, 51)
                self.multi_cell(170, 6, self._clean_text(stripped[4:]))
                self.ln(2)
                i += 1
                continue
                
            if stripped.startswith('#### '):
                self.ln(3)
                self.set_font('Helvetica', 'B', 10)
                self.set_text_color(68, 68, 68)
                self.multi_cell(170, 5, self._clean_text(stripped[5:]))
                self.ln(1)
                i += 1
                continue
            
            # Horizontale Linie
            if stripped in ['---', '***', '___']:
                self.ln(5)
                self.set_draw_color(200, 200, 200)
                self.line(20, self.get_y(), 190, self.get_y())
                self.ln(5)
                i += 1
                continue
            
            # Listen
            if stripped.startswith('- ') or stripped.startswith('* '):
                self.set_font('Helvetica', '', 10)
                self.set_text_color(64, 64, 64)
                self.cell(8, 5, chr(149))  # Bullet point
                self.multi_cell(162, 5, self._clean_text(stripped[2:]))
                i += 1
                continue
                
            if len(stripped) > 2 and stripped[0].isdigit() and '.' in stripped[:4]:
                self.set_font('Helvetica', '', 10)
                self.set_text_color(64, 64, 64)
                dot_pos = stripped.find('.')
                num = stripped[:dot_pos]
                self.cell(10, 5, f"{num}.")
                self.multi_cell(160, 5, self._clean_text(stripped[dot_pos+1:].strip()))
                i += 1
                continue
            
            # Normaler Text
            self.set_font('Helvetica', '', 10)
            self.set_text_color(26, 26, 26)
            text = self._clean_text(stripped)
            if text:
                self.multi_cell(170, 5, text)
            
            i += 1
        
        # Falls Tabelle am Ende
        if in_table and table_rows:
            self.render_table(table_rows)
        
        # Footer mit Branding
        self.ln(10)
        self.set_draw_color(200, 200, 200)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(5)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        now = datetime.now()
        date_str = f"{now.day}. {GERMAN_MONTHS[now.month]} {now.year}"
        self.cell(0, 5, f"Generiert am {date_str}", align='C')
        self.ln(4)
        self.cell(0, 5, "HayMAS - Dr. Hayward's AI Agent Army", align='C')
    
    def _clean_text(self, text: str) -> str:
        """Markdown-Formatierung entfernen."""
        # Bold und Italic
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        # Inline Code
        text = re.sub(r'`(.+?)`', r'\1', text)
        # Links
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
        # Sonderzeichen normalisieren
        text = text.replace('–', '-').replace('—', '-')
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('…', '...')
        text = text.replace('‑', '-')
        # Umlaute für FPDF
        replacements = {
            'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
            'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        # Nur druckbare ASCII
        return ''.join(c if ord(c) < 128 else '' for c in text)


def generate_pdf_from_markdown(md_content: str, title: str = "HayMAS Artikel") -> bytes:
    """
    Konvertiert Markdown zu PDF.
    
    Versucht zuerst WeasyPrint (beste Qualität), 
    fällt auf FPDF mit Tabellen-Support zurück.
    """
    # Titel aus H1 extrahieren
    h1_match = re.search(r'^#\s+(.+)$', md_content, re.MULTILINE)
    if h1_match:
        title = h1_match.group(1).strip()
    
    # Versuche WeasyPrint
    pdf_bytes = _try_weasyprint_pdf(md_content, title)
    if pdf_bytes:
        return pdf_bytes
    
    # Fallback: FPDF mit Tabellen-Support
    pdf = EnhancedPDF()
    pdf.render_markdown(md_content)
    return pdf.output()


@app.get("/api/articles/{filename}/pdf")
def get_article_pdf(filename: str):
    """
    Artikel als PDF herunterladen.
    
    Konvertiert die Markdown-Datei zu einem professionell gestalteten PDF
    mit WeasyPrint (Tabellen, Typography, Fußzeilen).
    """
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden")
    
    # Markdown laden
    with open(filepath, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    # PDF generieren
    try:
        pdf_bytes = generate_pdf_from_markdown(md_content, filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF-Generierung fehlgeschlagen: {str(e)}")
    
    # PDF-Dateiname
    pdf_filename = filename.replace('.md', '.pdf')
    
    return Response(
        content=bytes(pdf_bytes),
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


@app.post("/api/refine-prompt")
def refine_prompt(request: RefinePromptRequest):
    """
    Optimiert einen User-Prompt für bessere Ergebnisse.
    
    Kann regelbasiert (schnell) oder LLM-basiert (intelligenter) arbeiten.
    
    Returns:
        - analysis: Erkannte Parameter aus dem Prompt
        - optimized_prompt: Der optimierte Prompt
        - options: Verfügbare Optionen für das Frontend
    """
    optimizer = PromptOptimizerAgent()
    
    # Verfügbare Optionen für Frontend
    format_options = [
        {"value": "overview", "label": "Kompakte Übersicht", "pages": "3-5 Seiten", "description": "Kurzer Überblick über die wichtigsten Punkte"},
        {"value": "article", "label": "Fachartikel", "pages": "8-10 Seiten", "description": "Ausgewogener Artikel mit Tiefe"},
        {"value": "report", "label": "Expertenbericht", "pages": "10-15 Seiten", "description": "Umfassender Bericht mit allen Details"},
        {"value": "deep_dive", "label": "Deep-Dive Analyse", "pages": "15-20 Seiten", "description": "Tiefgehende Analyse für Spezialisten"}
    ]
    
    audience_options = [
        {"value": "experts", "label": "Fachexperten", "tone": "wissenschaftlich", "description": "Technisch präzise, setzt Vorwissen voraus"},
        {"value": "management", "label": "Management / Entscheider", "tone": "praxisorientiert", "description": "Strategisch, Business-fokussiert"},
        {"value": "general", "label": "Allgemein / Einsteiger", "tone": "erklärend", "description": "Einführend, erklärt Grundlagen"}
    ]
    
    if request.use_ai:
        # LLM-basierte Optimierung (langsamer, aber intelligenter)
        result = None
        for event in optimizer.analyze_and_optimize(
            request.question,
            user_preferences={
                "format": request.format,
                "audience": request.audience
            } if request.format or request.audience else None
        ):
            pass  # Events verarbeiten
        
        # Generator durchlaufen für Return-Wert
        gen = optimizer.analyze_and_optimize(
            request.question,
            user_preferences={
                "format": request.format,
                "audience": request.audience
            } if request.format or request.audience else None
        )
        try:
            while True:
                next(gen)
        except StopIteration as e:
            result = e.value
        
        return {
            **result,
            "options": {
                "formats": format_options,
                "audiences": audience_options
            }
        }
    else:
        # Regelbasierte Optimierung (schnell)
        format_choice = request.format or "report"
        audience_choice = request.audience or "experts"
        
        result = optimizer.quick_optimize(
            request.question,
            format_choice,
            audience_choice
        )
        
        return {
            **result,
            "options": {
                "formats": format_options,
                "audiences": audience_options
            }
        }


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
    1. evidence (DEFAULT): Evidence-Gated Flow - Claim-basiert, wissenschaftlich
    2. standard: Alter Flow (Recherche zuerst)
    3. deep: Deep Thinking (DEPRECATED)
    """
    
    tiers = request.tiers or {}
    mode = request.mode or "evidence"
    
    def event_stream():
        try:
            # ========== EVIDENCE-GATED MODE (NEU - DEFAULT) ==========
            if mode == "evidence":
                from evidence_gated.orchestrator import EvidenceGatedOrchestrator
                
                eg_orchestrator = EvidenceGatedOrchestrator(tiers=tiers)
                article_format = request.format or "report"
                
                for event in eg_orchestrator.process(request.question, format=article_format):
                    event_data = {
                        "type": event.event_type.value,
                        "agent": event.agent_name,
                        "content": event.content,
                        "data": event.data
                    }
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                
                yield "data: [DONE]\n\n"
                return
            
            # ========== STANDARD/DEEP MODE (Legacy) ==========
            # Agents erstellen
            orchestrator = OrchestratorAgent(tier=tiers.get("orchestrator", "premium"))
            researcher = ResearcherAgent(tier=tiers.get("researcher", "premium"))
            writer = WriterAgent(tier=tiers.get("writer", "premium"))
            editor = EditorAgent(tier=tiers.get("editor", "premium"))
            
            orchestrator.set_agents(researcher, writer, editor)
            
            # ========== DEEP THINKING MODE (DEPRECATED) ==========
            if mode == "deep":
                # Neuer Flow: LLM-Wissen zuerst, dann gezielte Recherche
                for event in orchestrator.process_article_deep(
                    core_question=request.question,
                    use_verification=True,  # Multi-LLM Verification
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
                return
            
            # ========== STANDARD MODE ==========
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
            
            # Generierung starten (Standard-Flow)
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


# ============================================================================
# STATIC FRONTEND (für Docker Container)
# ============================================================================

FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    # Built Frontend servieren (Docker/Production)
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
    
    @app.get("/")
    def serve_frontend():
        """Serve the frontend index.html"""
        return FileResponse(str(FRONTEND_DIST / "index.html"))
    
    @app.get("/{path:path}")
    def serve_frontend_routes(path: str):
        """Catch-all für SPA Routing"""
        # Statische Dateien direkt servieren
        file_path = FRONTEND_DIST / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        # Alles andere → index.html (SPA Routing)
        return FileResponse(str(FRONTEND_DIST / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

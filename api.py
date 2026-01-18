"""
HayMAS API Server
FastAPI Server für das React Frontend mit intelligenter Themenanalyse
"""

import os
import sys
import json
import glob
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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

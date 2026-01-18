"""
HayMAS Session Logger

Persistentes Logging für jeden Artikel-Generierungsprozess.
Wird nach jedem Schritt gespeichert - auch bei Abbruch verfügbar.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")


@dataclass
class AgentStep:
    """Ein einzelner Schritt im Generierungsprozess"""
    timestamp: str
    agent: str
    model: str
    provider: str
    tier: str
    action: str
    task: str
    duration_ms: Optional[int] = None
    tokens: Optional[Dict[str, int]] = None  # {"input": x, "output": y}
    tool_calls: List[str] = field(default_factory=list)
    status: str = "started"  # started, success, error
    result_length: Optional[int] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None  # Für Event-Details (z.B. Editor-Verdict)


@dataclass
class SessionLog:
    """Komplettes Log einer Session"""
    session_id: str
    started_at: str
    question: str
    settings: Dict[str, Any]
    timeline: List[AgentStep] = field(default_factory=list)
    status: str = "running"  # running, completed, aborted, error
    finished_at: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        """Konvertiert zu Dict für JSON-Serialisierung"""
        data = asdict(self)
        # Timeline separat konvertieren
        data["timeline"] = [asdict(step) for step in self.timeline]
        return data


class SessionLogger:
    """
    Logger für eine Artikel-Generierungs-Session.
    Speichert nach jedem Schritt persistent.
    """
    
    def __init__(
        self,
        question: str,
        settings: Dict[str, Any]
    ):
        os.makedirs(LOGS_DIR, exist_ok=True)
        
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log = SessionLog(
            session_id=self.session_id,
            started_at=datetime.now().isoformat(),
            question=question,
            settings=settings
        )
        self.log_path = os.path.join(LOGS_DIR, f"session_{self.session_id}.json")
        self._current_step_start: Optional[datetime] = None
        self._total_tokens = {"input": 0, "output": 0}
        
        # Initial speichern
        self._save()
    
    def start_step(
        self,
        agent: str,
        model: str,
        provider: str,
        tier: str,
        action: str,
        task: str
    ) -> int:
        """
        Startet einen neuen Schritt.
        Returns: Index des Schritts
        """
        self._current_step_start = datetime.now()
        
        step = AgentStep(
            timestamp=self._current_step_start.isoformat(),
            agent=agent,
            model=model,
            provider=provider,
            tier=tier,
            action=action,
            task=task[:500],  # Truncate für Übersichtlichkeit
            status="started"
        )
        self.log.timeline.append(step)
        self._save()
        
        return len(self.log.timeline) - 1
    
    def end_step(
        self,
        step_index: int,
        status: str = "success",
        tokens: Optional[Dict[str, int]] = None,
        tool_calls: List[str] = None,
        result_length: Optional[int] = None,
        error: Optional[str] = None
    ):
        """Beendet einen Schritt mit Ergebnis"""
        if step_index >= len(self.log.timeline):
            return
        
        step = self.log.timeline[step_index]
        
        # Dauer berechnen
        if self._current_step_start:
            duration = datetime.now() - self._current_step_start
            step.duration_ms = int(duration.total_seconds() * 1000)
        
        step.status = status
        step.tokens = tokens
        step.tool_calls = tool_calls or []
        step.result_length = result_length
        step.error = error
        
        # Token-Summe aktualisieren
        if tokens:
            self._total_tokens["input"] += tokens.get("input", 0)
            self._total_tokens["output"] += tokens.get("output", 0)
        
        self._save()
    
    def log_tool_call(self, step_index: int, tool_name: str):
        """Fügt einen Tool-Call zum aktuellen Schritt hinzu"""
        if step_index < len(self.log.timeline):
            self.log.timeline[step_index].tool_calls.append(tool_name)
            self._save()
    
    def log_event(self, event_data: Dict[str, Any]):
        """
        Loggt ein beliebiges Event (z.B. Editor-Verdict, Orchestrator-Entscheidung).
        Wird als separater Eintrag in der Timeline gespeichert.
        """
        # Events als spezieller AgentStep mit action="event"
        event_step = AgentStep(
            timestamp=datetime.now().isoformat(),
            agent="System",
            model="",
            provider="",
            tier="",
            action="event",
            task=event_data.get("type", "unknown_event"),
            status="success",
            details=event_data  # Event-Daten im korrekten Feld speichern
        )
        
        self.log.timeline.append(event_step)
        self._save()
    
    def complete(
        self,
        article_path: Optional[str] = None,
        article_words: Optional[int] = None
    ):
        """Markiert die Session als abgeschlossen"""
        self.log.status = "completed"
        self.log.finished_at = datetime.now().isoformat()
        
        # Summary erstellen
        started = datetime.fromisoformat(self.log.started_at)
        finished = datetime.fromisoformat(self.log.finished_at)
        total_duration = (finished - started).total_seconds() * 1000
        
        agents_used = [step.agent for step in self.log.timeline if step.status == "success"]
        
        self.log.summary = {
            "total_duration_ms": int(total_duration),
            "total_tokens": self._total_tokens,
            "estimated_cost_usd": self._estimate_cost(),
            "agents_used": agents_used,
            "steps_completed": len([s for s in self.log.timeline if s.status == "success"]),
            "steps_failed": len([s for s in self.log.timeline if s.status == "error"]),
            "article_path": article_path,
            "article_words": article_words
        }
        
        self._save()
    
    def abort(self, reason: str = "User cancelled"):
        """Markiert die Session als abgebrochen"""
        self.log.status = "aborted"
        self.log.finished_at = datetime.now().isoformat()
        
        # Letzten laufenden Schritt als abgebrochen markieren
        for step in reversed(self.log.timeline):
            if step.status == "started":
                step.status = "aborted"
                step.error = reason
                break
        
        self._save()
    
    def error(self, error_message: str):
        """Markiert die Session als fehlerhaft"""
        self.log.status = "error"
        self.log.finished_at = datetime.now().isoformat()
        
        # Letzten Schritt als Fehler markieren
        if self.log.timeline:
            self.log.timeline[-1].status = "error"
            self.log.timeline[-1].error = error_message
        
        self._save()
    
    def _estimate_cost(self) -> float:
        """Schätzt die Kosten basierend auf Token-Counts (grobe Schätzung)"""
        # Durchschnittspreise pro 1M Tokens (sehr grob)
        input_cost_per_million = 3.0   # ~$3 pro 1M Input
        output_cost_per_million = 15.0  # ~$15 pro 1M Output
        
        input_cost = (self._total_tokens["input"] / 1_000_000) * input_cost_per_million
        output_cost = (self._total_tokens["output"] / 1_000_000) * output_cost_per_million
        
        return round(input_cost + output_cost, 4)
    
    def _save(self):
        """Speichert das Log persistent"""
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self.log.to_dict(), f, ensure_ascii=False, indent=2)
    
    def get_log_filename(self) -> str:
        """Gibt den Dateinamen des Logs zurück"""
        return f"session_{self.session_id}.json"


def get_log_for_article(article_filename: str) -> Optional[Dict]:
    """
    Findet das Log für einen Artikel basierend auf dem Timestamp.
    Artikel: wie_funktionieren_..._20260117_212309.md
    Log: session_20260117_212309.json
    """
    # Timestamp aus Artikelname extrahieren
    parts = article_filename.replace(".md", "").split("_")
    if len(parts) >= 2:
        # Die letzten beiden Teile sind Datum und Zeit
        timestamp = f"{parts[-2]}_{parts[-1]}"
        log_path = os.path.join(LOGS_DIR, f"session_{timestamp}.json")
        
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                return json.load(f)
    
    return None


def list_all_logs() -> List[Dict]:
    """Listet alle verfügbaren Logs"""
    os.makedirs(LOGS_DIR, exist_ok=True)
    logs = []
    
    for filename in sorted(os.listdir(LOGS_DIR), reverse=True):
        if filename.startswith("session_") and filename.endswith(".json"):
            filepath = os.path.join(LOGS_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    log = json.load(f)
                    logs.append({
                        "filename": filename,
                        "session_id": log.get("session_id"),
                        "question": log.get("question", "")[:100],
                        "status": log.get("status"),
                        "started_at": log.get("started_at")
                    })
            except:
                pass
    
    return logs

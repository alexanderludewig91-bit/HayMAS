import { Loader2, Square, CheckCircle, Edit3, Search, AlertTriangle, ArrowRight } from 'lucide-react';
import type { AgentEvent, EditorVerdict } from '../types';

interface ProducingViewProps {
  question: string;
  events: AgentEvent[];
  onCancel: () => void;
  isFinished?: boolean;
  onViewArticle?: () => void;
}

const phaseFromEvents = (events: AgentEvent[]): string => {
  const lastStatus = [...events].reverse().find((e) => e.type === 'status');
  if (!lastStatus) return 'Starte...';

  const content = lastStatus.content.toLowerCase();
  if (content.includes('nachrecherche')) return 'Nachrecherche';
  if (content.includes('recherche')) return 'Recherche';
  if (content.includes('writer') || content.includes('artikel')) return 'Schreiben';
  if (content.includes('editor-verdict') || content.includes('orchestrator-entscheidung')) return 'Bewertung';
  if (content.includes('editor')) return 'Überarbeitung';
  return 'Verarbeitung';
};

const eventIcon = (type: AgentEvent['type']): string => {
  switch (type) {
    case 'thinking':
      return '🤔';
    case 'tool_call':
      return '🔧';
    case 'tool_result':
      return '📦';
    case 'response':
      return '✅';
    case 'error':
      return '❌';
    case 'status':
      return 'ℹ️';
    default:
      return '•';
  }
};

// Spezielle Darstellung für Editor-Verdicts
const EditorVerdictDisplay = ({ verdict }: { verdict: EditorVerdict }) => {
  const verdictConfig = {
    approved: { 
      icon: CheckCircle, 
      color: 'text-green-600 bg-green-50 border-green-200',
      label: 'Genehmigt'
    },
    revise: { 
      icon: Edit3, 
      color: 'text-amber-600 bg-amber-50 border-amber-200',
      label: 'Überarbeitung'
    },
    research: { 
      icon: Search, 
      color: 'text-blue-600 bg-blue-50 border-blue-200',
      label: 'Nachrecherche'
    },
  };
  
  const config = verdictConfig[verdict.verdict] || verdictConfig.revise;
  const Icon = config.icon;
  
  return (
    <div className={`p-4 rounded-lg border ${config.color}`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon size={18} />
        <span className="font-semibold">{config.label}</span>
        <span className="text-xs opacity-70">
          ({Math.round(verdict.confidence * 100)}% Konfidenz)
        </span>
      </div>
      
      {verdict.issues && verdict.issues.length > 0 && (
        <div className="mt-2 space-y-1">
          {verdict.issues.slice(0, 3).map((issue, idx) => (
            <div key={idx} className="flex items-start gap-2 text-sm">
              <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-medium capitalize">{issue.type.replace('_', ' ')}</span>
                <span className="mx-1">·</span>
                <span className="opacity-80">{issue.description}</span>
                {issue.research_query && (
                  <span className="block text-xs opacity-60 mt-0.5">
                    → Recherche: "{issue.research_query}"
                  </span>
                )}
              </div>
            </div>
          ))}
          {verdict.issues.length > 3 && (
            <div className="text-xs opacity-60">
              +{verdict.issues.length - 3} weitere Issues
            </div>
          )}
        </div>
      )}
      
      {verdict.summary && (
        <p className="mt-2 text-sm opacity-80">{verdict.summary}</p>
      )}
    </div>
  );
};

export function ProducingView({ question, events, onCancel, isFinished, onViewArticle }: ProducingViewProps) {
  const phase = phaseFromEvents(events);
  const progress = isFinished ? 100 : Math.min((events.length / 30) * 100, 95);
  
  // Events umkehren - neueste oben
  const reversedEvents = [...events].reverse();

  return (
    <div className="flex-1 flex flex-col max-w-3xl mx-auto w-full p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 text-neutral-900">
            {isFinished ? (
              <CheckCircle size={18} className="text-green-600" />
            ) : (
              <Loader2 size={18} className="animate-spin" />
            )}
            <span className="font-medium">{isFinished ? 'Abgeschlossen' : phase}</span>
            <span className="text-xs text-neutral-400 ml-2">
              {events.length} Schritte
            </span>
          </div>
          {isFinished ? (
            <button
              onClick={onViewArticle}
              className="flex items-center gap-2 px-4 py-2 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
            >
              Zum Artikel
              <ArrowRight size={16} />
            </button>
          ) : (
            <button
              onClick={onCancel}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 rounded-lg transition-colors"
            >
              <Square size={14} />
              Abbrechen
            </button>
          )}
        </div>
        <p className="text-sm text-neutral-500 truncate">{question}</p>
      </div>

      {/* Progress */}
      <div className="h-1 bg-neutral-100 rounded-full mb-6 overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${isFinished ? 'bg-green-600' : 'bg-neutral-900'}`}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Events - neueste oben */}
      <div className="flex-1 overflow-y-auto space-y-2">
        {reversedEvents.map((event, i) => {
          const originalIndex = events.length - 1 - i;
          // Prüfe ob dies ein Editor-Verdict Event ist
          const verdictData = event.data?.verdict as EditorVerdict | undefined;
          const isVerdictEvent = verdictData && verdictData.verdict;
          
          // Spezielle Darstellung für Editor-Verdict
          if (isVerdictEvent) {
            return (
              <div key={originalIndex} className="space-y-2">
                <div className="flex items-center gap-2 text-xs text-neutral-500">
                  <span className="font-medium">{event.agent}</span>
                  <span>·</span>
                  <span>Editor-Bewertung</span>
                  <span className="text-neutral-400 ml-auto">#{originalIndex + 1}</span>
                </div>
                <EditorVerdictDisplay verdict={verdictData} />
              </div>
            );
          }
          
          // Standard Event-Darstellung mit mehr Details
          const eventTypeLabel = {
            thinking: 'Denkt...',
            tool_call: 'Tool-Aufruf',
            tool_result: 'Tool-Ergebnis',
            response: 'Antwort',
            error: 'Fehler',
            status: 'Status'
          }[event.type] || event.type;
          
          return (
            <div
              key={originalIndex}
              className={`p-3 rounded-lg text-sm ${
                event.type === 'error'
                  ? 'bg-red-50 border-l-2 border-red-400'
                  : event.type === 'response'
                  ? 'bg-green-50 border-l-2 border-green-400'
                  : event.content.includes('Orchestrator-Entscheidung')
                  ? 'bg-purple-50 border-l-2 border-purple-400'
                  : event.content.includes('Nachrecherche')
                  ? 'bg-blue-50 border-l-2 border-blue-400'
                  : event.type === 'tool_call' || event.type === 'tool_result'
                  ? 'bg-amber-50 border-l-2 border-amber-300'
                  : 'bg-neutral-50 border-l-2 border-neutral-200'
              }`}
            >
              <div className="flex items-start gap-2">
                <span className="text-lg">{eventIcon(event.type)}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-neutral-900">{event.agent}</span>
                    <span className="text-xs px-1.5 py-0.5 bg-white/50 rounded text-neutral-500">
                      {eventTypeLabel}
                    </span>
                    <span className="text-xs text-neutral-400 ml-auto">#{originalIndex + 1}</span>
                  </div>
                  <p className="text-neutral-700 break-words">
                    {event.content.slice(0, 300)}
                    {event.content.length > 300 && '...'}
                  </p>
                  {/* Zusätzliche Details aus event.data */}
                  {event.data && Object.keys(event.data).length > 0 ? (
                    <div className="mt-2 pt-2 border-t border-black/5 text-xs text-neutral-500 flex flex-wrap gap-x-4 gap-y-1">
                      {event.data.article_path ? (
                        <div className="flex items-center gap-1">
                          <span>📄</span>
                          <span className="font-mono">{String(event.data.article_path).split('/').pop()}</span>
                        </div>
                      ) : null}
                      {event.data.claims_count ? (
                        <span>✓ {String(event.data.claims_count)} Claims</span>
                      ) : null}
                      {event.data.a_claims !== undefined ? (
                        <span className="text-green-600">A:{String(event.data.a_claims)}</span>
                      ) : null}
                      {event.data.b_claims !== undefined ? (
                        <span className="text-blue-600">B:{String(event.data.b_claims)}</span>
                      ) : null}
                      {event.data.c_claims !== undefined ? (
                        <span className="text-amber-600">C:{String(event.data.c_claims)}</span>
                      ) : null}
                      {event.data.total_sources ? (
                        <span>📚 {String(event.data.total_sources)} Quellen</span>
                      ) : null}
                      {event.data.claims_fulfilled !== undefined && event.data.claims_processed ? (
                        <span>✅ {String(event.data.claims_fulfilled)}/{String(event.data.claims_processed)} Claims erfüllt</span>
                      ) : null}
                      {event.data.tools_used && Array.isArray(event.data.tools_used) ? (
                        <span>🔧 {(event.data.tools_used as string[]).join(', ')}</span>
                      ) : null}
                      {event.data.word_count ? (
                        <span>📝 {String(event.data.word_count)} Wörter</span>
                      ) : null}
                      {event.data.char_count ? (
                        <span>({Math.round(Number(event.data.char_count) / 1000)}k Zeichen)</span>
                      ) : null}
                      {event.data.sources_rated ? (
                        <span>⚖️ {String(event.data.sources_rated)} bewertet</span>
                      ) : null}
                      {event.data.model_used ? (
                        <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded">{String(event.data.model_used)}</span>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

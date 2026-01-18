import { Loader2, Square, CheckCircle, Edit3, Search, AlertTriangle } from 'lucide-react';
import type { AgentEvent, EditorVerdict } from '../types';

interface ProducingViewProps {
  question: string;
  events: AgentEvent[];
  onCancel: () => void;
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

export function ProducingView({ question, events, onCancel }: ProducingViewProps) {
  const phase = phaseFromEvents(events);
  const progress = Math.min((events.length / 30) * 100, 95);

  return (
    <div className="flex-1 flex flex-col max-w-3xl mx-auto w-full p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 text-neutral-900">
            <Loader2 size={18} className="animate-spin" />
            <span className="font-medium">{phase}</span>
          </div>
          <button
            onClick={onCancel}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 rounded-lg transition-colors"
          >
            <Square size={14} />
            Abbrechen
          </button>
        </div>
        <p className="text-sm text-neutral-500 truncate">{question}</p>
      </div>

      {/* Progress */}
      <div className="h-1 bg-neutral-100 rounded-full mb-6 overflow-hidden">
        <div
          className="h-full bg-neutral-900 transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Events */}
      <div className="flex-1 overflow-y-auto space-y-2">
        {events.map((event, i) => {
          // Prüfe ob dies ein Editor-Verdict Event ist
          const verdictData = event.data?.verdict as EditorVerdict | undefined;
          const isVerdictEvent = verdictData && verdictData.verdict;
          
          // Spezielle Darstellung für Editor-Verdict
          if (isVerdictEvent) {
            return (
              <div key={i} className="space-y-2">
                <div className="flex items-center gap-2 text-xs text-neutral-500">
                  <span>{event.agent}</span>
                  <span>·</span>
                  <span>Editor-Bewertung</span>
                </div>
                <EditorVerdictDisplay verdict={verdictData} />
              </div>
            );
          }
          
          // Standard Event-Darstellung
          return (
            <div
              key={i}
              className={`p-3 rounded-lg text-sm ${
                event.type === 'error'
                  ? 'bg-red-50 border-l-2 border-red-400'
                  : event.type === 'response'
                  ? 'bg-green-50 border-l-2 border-green-400'
                  : event.content.includes('Orchestrator-Entscheidung')
                  ? 'bg-purple-50 border-l-2 border-purple-400'
                  : event.content.includes('Nachrecherche')
                  ? 'bg-blue-50 border-l-2 border-blue-400'
                  : 'bg-neutral-50 border-l-2 border-neutral-200'
              }`}
            >
              <div className="flex items-start gap-2">
                <span>{eventIcon(event.type)}</span>
                <div className="flex-1 min-w-0">
                  <span className="font-medium text-neutral-900">{event.agent}</span>
                  <p className="text-neutral-600 break-words">
                    {event.content.slice(0, 200)}
                    {event.content.length > 200 && '...'}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

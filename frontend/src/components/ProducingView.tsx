import { Loader2, Square } from 'lucide-react';
import type { AgentEvent } from '../types';

interface ProducingViewProps {
  question: string;
  events: AgentEvent[];
  onCancel: () => void;
}

const phaseFromEvents = (events: AgentEvent[]): string => {
  const lastStatus = [...events].reverse().find((e) => e.type === 'status');
  if (!lastStatus) return 'Starte...';

  const content = lastStatus.content.toLowerCase();
  if (content.includes('recherche')) return 'Recherche';
  if (content.includes('writer') || content.includes('artikel')) return 'Schreiben';
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
        {events.map((event, i) => (
          <div
            key={i}
            className={`p-3 rounded-lg text-sm ${
              event.type === 'error'
                ? 'bg-red-50 border-l-2 border-red-400'
                : event.type === 'response'
                ? 'bg-green-50 border-l-2 border-green-400'
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
        ))}
      </div>
    </div>
  );
}

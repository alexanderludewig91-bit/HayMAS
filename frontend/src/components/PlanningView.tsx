import { Play, ArrowLeft, Check, X, Edit2, GripVertical, Sparkles, Globe, BookOpen, Newspaper, MessageSquare, DollarSign, GraduationCap, FileText, Building2 } from 'lucide-react';
import type { ResearchPlan, ResearchRound, ResearchTool, Tier } from '../types';
import { useState } from 'react';

// Tool-Konfiguration für die UI
const TOOL_CONFIG: Record<ResearchTool, { icon: React.ReactNode; name: string; color: string }> = {
  tavily: { icon: <Globe size={14} />, name: 'Web Search', color: 'text-blue-600 bg-blue-50' },
  wikipedia: { icon: <BookOpen size={14} />, name: 'Wikipedia', color: 'text-emerald-600 bg-emerald-50' },
  gnews: { icon: <Newspaper size={14} />, name: 'Google News', color: 'text-amber-600 bg-amber-50' },
  hackernews: { icon: <MessageSquare size={14} />, name: 'Hacker News', color: 'text-orange-600 bg-orange-50' },
  semantic_scholar: { icon: <GraduationCap size={14} />, name: 'Semantic Scholar', color: 'text-purple-600 bg-purple-50' },
  arxiv: { icon: <FileText size={14} />, name: 'arXiv', color: 'text-red-600 bg-red-50' },
  ted: { icon: <Building2 size={14} />, name: 'TED EU-Ausschreibungen', color: 'text-indigo-600 bg-indigo-50' },
};

interface PlanningViewProps {
  question: string;
  plan: ResearchPlan;
  tiers: Record<string, Tier>;
  onUpdatePlan: (plan: ResearchPlan) => void;
  onToggleRound: (index: number) => void;
  onUpdateRound: (index: number, updates: Partial<ResearchRound>) => void;
  onSetUseEditor: (use: boolean) => void;
  onSetTier: (agent: string, tier: Tier) => void;
  onStart: () => void;
  onBack: () => void;
}

export function PlanningView({
  question,
  plan,
  tiers,
  onToggleRound,
  onUpdateRound,
  onSetUseEditor,
  onSetTier,
  onStart,
  onBack,
}: PlanningViewProps) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editValue, setEditValue] = useState('');
  const [showModelSettings, setShowModelSettings] = useState(false);

  const activeRounds = plan.rounds.filter((r) => r.enabled).length;
  
  // Berechne geschätzte Kosten basierend auf aktiven Tiers
  const estimateCost = () => {
    const costs: Record<string, Record<Tier, number>> = {
      orchestrator: { premium: 0.05, budget: 0.02 },
      researcher: { premium: 0.03, budget: 0.01 },
      writer: { premium: 0.15, budget: 0.08 },
      editor: { premium: 0.05, budget: 0.01 },
    };
    
    let total = costs.orchestrator[tiers.orchestrator || 'premium'];
    total += activeRounds * costs.researcher[tiers.researcher || 'premium'];
    total += (plan.use_editor ? 2 : 1) * costs.writer[tiers.writer || 'premium'];
    if (plan.use_editor) total += costs.editor[tiers.editor || 'premium'];
    
    return total.toFixed(2);
  };

  const handleEditStart = (index: number, currentQuery: string) => {
    setEditingIndex(index);
    setEditValue(currentQuery);
  };

  const handleEditSave = (index: number) => {
    onUpdateRound(index, { search_query: editValue });
    setEditingIndex(null);
  };

  const handleEditCancel = () => {
    setEditingIndex(null);
    setEditValue('');
  };

  return (
    <div className="flex-1 flex flex-col p-6 max-w-3xl mx-auto w-full">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-700 mb-4"
        >
          <ArrowLeft size={16} />
          Zurück
        </button>
        
        <h1 className="text-xl font-semibold text-neutral-900 mb-1">
          Recherche-Plan
        </h1>
        <p className="text-sm text-neutral-500 line-clamp-2">
          {question}
        </p>
      </div>

      {/* Plan Info */}
      <div className="bg-neutral-50 rounded-lg p-4 mb-6 text-sm">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles size={16} className="text-amber-500" />
          <span className="font-medium text-neutral-700">KI-Empfehlung</span>
        </div>
        <p className="text-neutral-600">{plan.reasoning}</p>
        <div className="flex gap-4 mt-3 text-xs text-neutral-500">
          <span>Typ: <strong>{plan.topic_type}</strong></span>
          <span>Aktualität: <strong>{plan.time_relevance}</strong></span>
          <span>Komplexität: <strong>{plan.complexity}</strong></span>
        </div>
      </div>

      {/* Research Rounds */}
      <div className="flex-1 overflow-auto">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-neutral-700">
            Recherche-Runden ({activeRounds} aktiv)
          </h2>
        </div>

        <div className="space-y-2">
          {plan.rounds.map((round, index) => (
            <div
              key={index}
              className={`border rounded-lg p-4 transition-colors ${
                round.enabled
                  ? 'border-neutral-200 bg-white'
                  : 'border-neutral-100 bg-neutral-50 opacity-60'
              }`}
            >
              <div className="flex items-start gap-3">
                {/* Drag Handle (visual only for now) */}
                <div className="mt-1 text-neutral-300">
                  <GripVertical size={16} />
                </div>

                {/* Toggle */}
                <button
                  onClick={() => onToggleRound(index)}
                  className={`mt-1 w-5 h-5 rounded border flex items-center justify-center flex-shrink-0 transition-colors ${
                    round.enabled
                      ? 'bg-neutral-900 border-neutral-900 text-white'
                      : 'border-neutral-300 bg-white'
                  }`}
                >
                  {round.enabled && <Check size={12} />}
                </button>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-neutral-400">
                      #{index + 1}
                    </span>
                    <span className="font-medium text-neutral-900">
                      {round.name}
                    </span>
                  </div>
                  
                  <p className="text-sm text-neutral-500 mb-2">
                    {round.focus}
                  </p>

                  {/* Tool-Auswahl */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs text-neutral-400">Tool:</span>
                    <select
                      value={round.tool || 'tavily'}
                      onChange={(e) => onUpdateRound(index, { tool: e.target.value as ResearchTool })}
                      className={`text-xs px-2 py-1 rounded-full border-0 font-medium cursor-pointer ${TOOL_CONFIG[round.tool || 'tavily'].color}`}
                    >
                      {Object.entries(TOOL_CONFIG).map(([id, config]) => (
                        <option key={id} value={id}>{config.name}</option>
                      ))}
                    </select>
                  </div>

                  {/* Editable Search Query */}
                  {editingIndex === index ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        className="flex-1 text-sm px-2 py-1 border border-neutral-300 rounded focus:outline-none focus:ring-1 focus:ring-neutral-400"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleEditSave(index);
                          if (e.key === 'Escape') handleEditCancel();
                        }}
                      />
                      <button
                        onClick={() => handleEditSave(index)}
                        className="p-1 text-green-600 hover:bg-green-50 rounded"
                      >
                        <Check size={16} />
                      </button>
                      <button
                        onClick={handleEditCancel}
                        className="p-1 text-red-600 hover:bg-red-50 rounded"
                      >
                        <X size={16} />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 group">
                      <code className="text-xs bg-neutral-100 px-2 py-1 rounded text-neutral-600 flex-1 truncate">
                        {round.search_query}
                      </code>
                      <button
                        onClick={() => handleEditStart(index, round.search_query)}
                        className="p-1 text-neutral-400 hover:text-neutral-600 opacity-0 group-hover:opacity-100 transition-opacity"
                        title="Suchanfrage bearbeiten"
                      >
                        <Edit2 size={14} />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Editor Toggle */}
      <div className="mt-6 pt-4 border-t border-neutral-200">
        <label className="flex items-center gap-3 cursor-pointer">
          <button
            onClick={() => onSetUseEditor(!plan.use_editor)}
            className={`w-10 h-6 rounded-full transition-colors relative ${
              plan.use_editor ? 'bg-neutral-900' : 'bg-neutral-200'
            }`}
          >
            <span
              className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                plan.use_editor ? 'translate-x-5' : 'translate-x-1'
              }`}
            />
          </button>
          <div>
            <span className="text-sm font-medium text-neutral-700">
              Editor-Review aktivieren
            </span>
            <p className="text-xs text-neutral-500">
              Ein Editor-Agent prüft den Artikel und gibt Verbesserungsvorschläge
            </p>
          </div>
        </label>
      </div>

      {/* Model Settings (Collapsible) */}
      <div className="mt-4 pt-4 border-t border-neutral-200">
        <button
          onClick={() => setShowModelSettings(!showModelSettings)}
          className="flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900"
        >
          <DollarSign size={16} />
          <span>Modell-Einstellungen</span>
          <span className="text-xs text-neutral-400 ml-2">
            (geschätzt ~${estimateCost()})
          </span>
          <span className={`transition-transform ${showModelSettings ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </button>
        
        {showModelSettings && (
          <div className="mt-3 space-y-2">
            {plan.model_recommendations && (
              <p className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded mb-2">
                💡 KI-Empfehlung basierend auf Komplexität: {plan.complexity}
              </p>
            )}
            
            {(['orchestrator', 'researcher', 'writer', 'editor'] as const).map((agent) => {
              const isRecommended = plan.model_recommendations?.[agent];
              const currentTier = tiers[agent] || 'premium';
              
              return (
                <div key={agent} className="flex items-center justify-between py-1">
                  <span className="text-sm text-neutral-600 capitalize">{agent}</span>
                  <div className="flex items-center gap-2">
                    {isRecommended && isRecommended !== currentTier && (
                      <span className="text-xs text-amber-500">
                        (empfohlen: {isRecommended})
                      </span>
                    )}
                    <select
                      value={currentTier}
                      onChange={(e) => onSetTier(agent, e.target.value as Tier)}
                      className={`text-xs px-2 py-1 rounded border ${
                        currentTier === 'premium' 
                          ? 'border-amber-300 bg-amber-50 text-amber-700' 
                          : 'border-neutral-200 bg-neutral-50 text-neutral-600'
                      }`}
                    >
                      <option value="premium">Premium</option>
                      <option value="budget">Budget</option>
                    </select>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="mt-6 flex gap-3">
        <button
          onClick={onBack}
          className="px-4 py-3 border border-neutral-200 text-neutral-700 rounded-lg font-medium hover:bg-neutral-50 transition-colors"
        >
          Abbrechen
        </button>
        <button
          onClick={onStart}
          disabled={activeRounds === 0}
          className="flex-1 py-3 bg-neutral-900 text-white rounded-lg font-medium hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          <Play size={18} />
          <span>Mit {activeRounds} Runden starten</span>
          <span className="text-neutral-400 text-sm">(~${estimateCost()})</span>
        </button>
      </div>
    </div>
  );
}

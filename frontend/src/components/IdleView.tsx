import { Sparkles, Zap, Settings2 } from 'lucide-react';

interface IdleViewProps {
  question: string;
  onQuestionChange: (q: string) => void;
  onAnalyze: () => void;
  onQuickStart: () => void;
  isAnalyzing: boolean;
}

export function IdleView({ 
  question, 
  onQuestionChange, 
  onAnalyze, 
  onQuickStart,
  isAnalyzing 
}: IdleViewProps) {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim()) {
      onAnalyze();
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-6">
      <div className="w-full max-w-xl">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-semibold text-neutral-900 mb-2">
            Wissensartikel erstellen
          </h1>
          <p className="text-neutral-500">
            Beschreibe ein Thema und lass KI-Agenten einen Artikel generieren
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            value={question}
            onChange={(e) => onQuestionChange(e.target.value)}
            placeholder="z.B.: Wie funktioniert Retrieval Augmented Generation (RAG)?"
            className="w-full h-32 px-4 py-3 border border-neutral-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent text-neutral-900 placeholder:text-neutral-400"
            autoFocus
            disabled={isAnalyzing}
          />

          <div className="flex gap-3">
            {/* Hauptbutton: Plan erstellen */}
            <button
              type="submit"
              disabled={!question.trim() || isAnalyzing}
              className="flex-1 py-3 bg-neutral-900 text-white rounded-lg font-medium hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {isAnalyzing ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Analysiere...
                </>
              ) : (
                <>
                  <Settings2 size={18} />
                  Plan erstellen
                </>
              )}
            </button>

            {/* Sekundärbutton: Schnellstart */}
            <button
              type="button"
              onClick={onQuickStart}
              disabled={!question.trim() || isAnalyzing}
              className="py-3 px-4 border border-neutral-200 text-neutral-700 rounded-lg font-medium hover:bg-neutral-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              title="Direkt starten ohne Plan-Vorschau"
            >
              <Zap size={18} />
              Schnellstart
            </button>
          </div>
        </form>

        <p className="text-center text-xs text-neutral-400 mt-3">
          <strong>Plan erstellen:</strong> Recherche-Strategie anpassen • <strong>Schnellstart:</strong> Direkt generieren
        </p>

        <div className="mt-6 flex gap-2 justify-center">
          <button
            type="button"
            onClick={() => onQuestionChange('Wie beeinflusst KI die ServiceNow Plattform? Gehe insbesondere auf Now Assist und die Agentic AI Funktionen ein.')}
            className="text-sm text-neutral-500 hover:text-neutral-700 px-3 py-1 rounded hover:bg-neutral-100 transition-colors"
            disabled={isAnalyzing}
          >
            Beispiel: ServiceNow
          </button>
          <button
            type="button"
            onClick={() => onQuestionChange('Warum ist die Banane krumm?')}
            className="text-sm text-neutral-500 hover:text-neutral-700 px-3 py-1 rounded hover:bg-neutral-100 transition-colors"
            disabled={isAnalyzing}
          >
            Beispiel: Banane
          </button>
          <button
            type="button"
            onClick={() => onQuestionChange('Was sind aktuelle KI Tools für AI Coding neben Cursor? Welche neuen Tools gibt es 2025/2026?')}
            className="text-sm text-neutral-500 hover:text-neutral-700 px-3 py-1 rounded hover:bg-neutral-100 transition-colors"
            disabled={isAnalyzing}
          >
            Beispiel: AI Coding
          </button>
        </div>
      </div>
    </div>
  );
}

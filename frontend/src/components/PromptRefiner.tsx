import { useState, useEffect } from 'react';
import { X, FileText, BookOpen, FileSearch, Microscope, Users, Briefcase, GraduationCap, Wand2, Check, Loader2 } from 'lucide-react';

interface FormatOption {
  value: string;
  label: string;
  pages: string;
  description: string;
}

interface AudienceOption {
  value: string;
  label: string;
  tone: string;
  description: string;
}

interface OptimizedPrompt {
  prompt_text: string;
  parameters: {
    target_pages: number;
    audience: string;
    tone: string;
    format: string;
  };
  explanation: string;
}

interface PromptRefinerProps {
  isOpen: boolean;
  originalPrompt: string;
  onClose: () => void;
  onConfirm: (optimizedPrompt: string, parameters: OptimizedPrompt['parameters']) => void;
}

const FORMAT_ICONS: Record<string, React.ReactNode> = {
  overview: <FileText size={20} />,
  article: <BookOpen size={20} />,
  report: <FileSearch size={20} />,
  deep_dive: <Microscope size={20} />,
};

const AUDIENCE_ICONS: Record<string, React.ReactNode> = {
  experts: <GraduationCap size={20} />,
  management: <Briefcase size={20} />,
  general: <Users size={20} />,
};

const DEFAULT_FORMATS: FormatOption[] = [
  { value: 'overview', label: 'Kompakte Übersicht', pages: '3-5 Seiten', description: 'Kurzer Überblick über die wichtigsten Punkte' },
  { value: 'article', label: 'Fachartikel', pages: '8-10 Seiten', description: 'Ausgewogener Artikel mit Tiefe' },
  { value: 'report', label: 'Expertenbericht', pages: '10-15 Seiten', description: 'Umfassender Bericht mit allen Details' },
  { value: 'deep_dive', label: 'Deep-Dive Analyse', pages: '15-20 Seiten', description: 'Tiefgehende Analyse für Spezialisten' },
];

const DEFAULT_AUDIENCES: AudienceOption[] = [
  { value: 'experts', label: 'Fachexperten', tone: 'wissenschaftlich', description: 'Technisch präzise, setzt Vorwissen voraus' },
  { value: 'management', label: 'Management / Entscheider', tone: 'praxisorientiert', description: 'Strategisch, Business-fokussiert' },
  { value: 'general', label: 'Allgemein / Einsteiger', tone: 'erklärend', description: 'Einführend, erklärt Grundlagen' },
];

export function PromptRefiner({ isOpen, originalPrompt, onClose, onConfirm }: PromptRefinerProps) {
  const [selectedFormat, setSelectedFormat] = useState<string>('report');
  const [selectedAudience, setSelectedAudience] = useState<string>('experts');
  const [optimizedPrompt, setOptimizedPrompt] = useState<OptimizedPrompt | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [editedPrompt, setEditedPrompt] = useState<string>('');
  const [isEditing, setIsEditing] = useState(false);

  // Optimierten Prompt vom Backend laden wenn sich Auswahl ändert
  useEffect(() => {
    if (!isOpen || !originalPrompt) return;

    const fetchOptimizedPrompt = async () => {
      setIsLoading(true);
      try {
        const response = await fetch('http://localhost:8000/api/refine-prompt', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question: originalPrompt,
            format: selectedFormat,
            audience: selectedAudience,
            use_ai: false, // Regelbasiert für Schnelligkeit
          }),
        });

        if (response.ok) {
          const data = await response.json();
          setOptimizedPrompt(data.optimized_prompt);
          setEditedPrompt(data.optimized_prompt.prompt_text);
        }
      } catch (error) {
        console.error('Fehler beim Optimieren:', error);
        // Fallback
        setOptimizedPrompt({
          prompt_text: `Erstelle einen Expertenbericht über: ${originalPrompt}`,
          parameters: {
            target_pages: 12,
            audience: 'Fachexperten',
            tone: 'wissenschaftlich',
            format: 'Expertenbericht',
          },
          explanation: 'Fallback-Optimierung',
        });
        setEditedPrompt(`Erstelle einen Expertenbericht über: ${originalPrompt}`);
      } finally {
        setIsLoading(false);
      }
    };

    fetchOptimizedPrompt();
  }, [isOpen, originalPrompt, selectedFormat, selectedAudience]);

  if (!isOpen) return null;

  const handleConfirm = () => {
    if (optimizedPrompt) {
      onConfirm(
        isEditing ? editedPrompt : optimizedPrompt.prompt_text,
        optimizedPrompt.parameters
      );
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-neutral-200">
          <div className="flex items-center gap-2">
            <Wand2 className="text-neutral-700" size={20} />
            <h2 className="text-lg font-semibold text-neutral-900">Prompt optimieren</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-neutral-100 rounded transition-colors"
          >
            <X size={20} className="text-neutral-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Original Prompt */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Deine Anfrage
            </label>
            <div className="bg-neutral-50 rounded-lg p-3 text-neutral-600 text-sm">
              {originalPrompt}
            </div>
          </div>

          {/* Format Selection */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-3">
              Format & Umfang
            </label>
            <div className="grid grid-cols-2 gap-3">
              {DEFAULT_FORMATS.map((format) => (
                <button
                  key={format.value}
                  onClick={() => setSelectedFormat(format.value)}
                  className={`flex items-start gap-3 p-3 rounded-lg border-2 text-left transition-all ${
                    selectedFormat === format.value
                      ? 'border-neutral-900 bg-neutral-50'
                      : 'border-neutral-200 hover:border-neutral-300'
                  }`}
                >
                  <div className={`mt-0.5 ${selectedFormat === format.value ? 'text-neutral-900' : 'text-neutral-400'}`}>
                    {FORMAT_ICONS[format.value]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-neutral-900 text-sm">{format.label}</div>
                    <div className="text-xs text-neutral-500">{format.pages}</div>
                    <div className="text-xs text-neutral-400 mt-1 truncate">{format.description}</div>
                  </div>
                  {selectedFormat === format.value && (
                    <Check size={16} className="text-neutral-900 mt-0.5" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Audience Selection */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-3">
              Zielgruppe
            </label>
            <div className="grid grid-cols-3 gap-3">
              {DEFAULT_AUDIENCES.map((audience) => (
                <button
                  key={audience.value}
                  onClick={() => setSelectedAudience(audience.value)}
                  className={`flex flex-col items-center gap-2 p-3 rounded-lg border-2 text-center transition-all ${
                    selectedAudience === audience.value
                      ? 'border-neutral-900 bg-neutral-50'
                      : 'border-neutral-200 hover:border-neutral-300'
                  }`}
                >
                  <div className={selectedAudience === audience.value ? 'text-neutral-900' : 'text-neutral-400'}>
                    {AUDIENCE_ICONS[audience.value]}
                  </div>
                  <div>
                    <div className="font-medium text-neutral-900 text-sm">{audience.label}</div>
                    <div className="text-xs text-neutral-400">{audience.description}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Optimized Prompt Preview */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-neutral-700">
                Optimierter Prompt
              </label>
              <button
                onClick={() => setIsEditing(!isEditing)}
                className="text-xs text-neutral-500 hover:text-neutral-700 transition-colors"
              >
                {isEditing ? 'Vorschau' : 'Bearbeiten'}
              </button>
            </div>
            {isLoading ? (
              <div className="bg-neutral-50 rounded-lg p-4 flex items-center justify-center">
                <Loader2 size={20} className="animate-spin text-neutral-400" />
                <span className="ml-2 text-sm text-neutral-500">Optimiere...</span>
              </div>
            ) : isEditing ? (
              <textarea
                value={editedPrompt}
                onChange={(e) => setEditedPrompt(e.target.value)}
                className="w-full h-32 px-3 py-2 border border-neutral-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent text-sm text-neutral-700"
              />
            ) : (
              <div className="bg-gradient-to-br from-neutral-50 to-neutral-100 rounded-lg p-4 border border-neutral-200">
                <p className="text-sm text-neutral-700 whitespace-pre-wrap">
                  {optimizedPrompt?.prompt_text || editedPrompt}
                </p>
                {optimizedPrompt?.explanation && (
                  <p className="text-xs text-neutral-400 mt-2 pt-2 border-t border-neutral-200">
                    💡 {optimizedPrompt.explanation}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Parameters Summary */}
          {optimizedPrompt && (
            <div className="flex flex-wrap gap-2">
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs">
                📄 {optimizedPrompt.parameters.target_pages} Seiten
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-50 text-green-700 rounded text-xs">
                👥 {optimizedPrompt.parameters.audience}
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-purple-50 text-purple-700 rounded text-xs">
                📝 {optimizedPrompt.parameters.tone}
              </span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-neutral-200 bg-neutral-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-neutral-600 hover:text-neutral-800 transition-colors"
          >
            Abbrechen
          </button>
          <button
            onClick={handleConfirm}
            disabled={isLoading || !optimizedPrompt}
            className="px-6 py-2 bg-neutral-900 text-white rounded-lg font-medium hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <Check size={16} />
            Übernehmen & Starten
          </button>
        </div>
      </div>
    </div>
  );
}

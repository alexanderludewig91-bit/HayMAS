import { X, Check } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { AgentTiers, ApiStatus, Tier } from '../types';
import { getStatus } from '../lib/api';

interface SettingsDrawerProps {
  open: boolean;
  onClose: () => void;
  tiers: AgentTiers;
  onTierChange: (agent: keyof AgentTiers, tier: Tier) => void;
}

const agents: { key: keyof AgentTiers; label: string; description: string }[] = [
  { key: 'orchestrator', label: 'Orchestrator', description: 'Koordiniert den Workflow' },
  { key: 'researcher', label: 'Researcher', description: 'Web-Recherche' },
  { key: 'writer', label: 'Writer', description: 'Schreibt den Artikel' },
  { key: 'editor', label: 'Editor', description: 'Qualitätsprüfung' },
];

export function SettingsDrawer({ 
  open, 
  onClose, 
  tiers, 
  onTierChange,
}: SettingsDrawerProps) {
  const [status, setStatus] = useState<ApiStatus | null>(null);

  useEffect(() => {
    if (open) {
      getStatus().then(setStatus);
    }
  }, [open]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed top-0 right-0 h-full w-80 bg-white shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-neutral-200">
          <h2 className="font-semibold text-neutral-900">Einstellungen</h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-neutral-100 text-neutral-500"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Info Box */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
            <strong>Hinweis:</strong> Recherche-Runden und Editor werden jetzt dynamisch pro Artikel im Plan-Editor konfiguriert.
          </div>

          {/* Model Tiers */}
          <div>
            <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
              Modell-Konfiguration
            </h3>
            <div className="space-y-3">
              {agents.map(({ key, label, description }) => (
                <div key={key} className="p-3 bg-neutral-50 rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm text-neutral-900">{label}</span>
                  </div>
                  <p className="text-xs text-neutral-500 mb-2">{description}</p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => onTierChange(key, 'premium')}
                      className={`flex-1 py-1.5 text-xs font-medium rounded transition-colors ${
                        tiers[key] === 'premium'
                          ? 'bg-neutral-900 text-white'
                          : 'bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-100'
                      }`}
                    >
                      Premium
                    </button>
                    <button
                      onClick={() => onTierChange(key, 'budget')}
                      className={`flex-1 py-1.5 text-xs font-medium rounded transition-colors ${
                        tiers[key] === 'budget'
                          ? 'bg-neutral-900 text-white'
                          : 'bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-100'
                      }`}
                    >
                      Budget
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* API Status */}
          <div>
            <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
              API Status
            </h3>
            {status ? (
              <div className="space-y-2">
                {Object.entries(status).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex items-center justify-between p-2 bg-neutral-50 rounded"
                  >
                    <span className="text-sm text-neutral-700 uppercase">{key}</span>
                    {value ? (
                      <Check size={16} className="text-green-500" />
                    ) : (
                      <X size={16} className="text-red-400" />
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-neutral-500">Laden...</div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

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

const agents: { key: keyof AgentTiers; label: string; description: string; premium: string; budget: string }[] = [
  { key: 'orchestrator', label: 'Orchestrator', description: 'Plant Claims & Struktur', premium: 'Claude Opus 4.5', budget: 'Claude Sonnet 4.5' },
  { key: 'writer', label: 'Writer', description: 'Schreibt den Artikel', premium: 'GPT-5.2', budget: 'GPT-5.1' },
  { key: 'editor', label: 'Editor', description: 'Qualitätsprüfung', premium: 'Claude Sonnet 4.5', budget: 'Claude Haiku 4.5' },
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
          {/* Model Tiers */}
          <div>
            <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
              Modell-Konfiguration
            </h3>
            <div className="space-y-3">
              {agents.map(({ key, label, description, premium, budget }) => (
                <div key={key} className="p-3 bg-neutral-50 rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm text-neutral-900">{label}</span>
                  </div>
                  <p className="text-xs text-neutral-500 mb-2">{description}</p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => onTierChange(key, 'premium')}
                      className={`flex-1 py-1.5 text-xs rounded transition-colors flex flex-col items-center ${
                        tiers[key] === 'premium'
                          ? 'bg-neutral-900 text-white'
                          : 'bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-100'
                      }`}
                    >
                      <span className="font-medium">Premium</span>
                      <span className={`text-[10px] ${tiers[key] === 'premium' ? 'text-neutral-300' : 'text-neutral-400'}`}>{premium}</span>
                    </button>
                    <button
                      onClick={() => onTierChange(key, 'budget')}
                      className={`flex-1 py-1.5 text-xs rounded transition-colors flex flex-col items-center ${
                        tiers[key] === 'budget'
                          ? 'bg-neutral-900 text-white'
                          : 'bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-100'
                      }`}
                    >
                      <span className="font-medium">Budget</span>
                      <span className={`text-[10px] ${tiers[key] === 'budget' ? 'text-neutral-300' : 'text-neutral-400'}`}>{budget}</span>
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

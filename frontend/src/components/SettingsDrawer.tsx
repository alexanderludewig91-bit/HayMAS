import { X, Check, Eye, EyeOff, Key, Save } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { AgentTiers, ApiStatus, Tier, WriterProvider } from '../types';
import { getSettings, saveApiKeys, type SettingsResponse } from '../lib/api';

interface SettingsDrawerProps {
  open: boolean;
  onClose: () => void;
  tiers: AgentTiers;
  onTierChange: (agent: keyof AgentTiers, tier: Tier) => void;
  onWriterProviderChange?: (provider: WriterProvider) => void;
}

// Agenten ohne Writer (der hat eigene Darstellung)
const agents: { key: keyof AgentTiers; label: string; description: string; premium: string; budget: string }[] = [
  { key: 'orchestrator', label: 'Orchestrator', description: 'Plant Claims & Struktur', premium: 'Claude Opus 4.5', budget: 'Claude Sonnet 4.5' },
  { key: 'editor', label: 'Editor', description: 'Qualitätsprüfung', premium: 'Claude Sonnet 4.5', budget: 'Claude Haiku 4.5' },
];

// Writer-Modelle pro Provider
const writerModels: Record<WriterProvider, { premium: string; budget: string }> = {
  openai: { premium: 'GPT-5.2', budget: 'GPT-5.1' },
  gemini: { premium: 'Gemini 3 Pro', budget: 'Gemini 2.5 Flash' },
};

export function SettingsDrawer({ 
  open, 
  onClose, 
  tiers, 
  onTierChange,
  onWriterProviderChange,
}: SettingsDrawerProps) {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [status, setStatus] = useState<ApiStatus | null>(null);
  const writerProvider: WriterProvider = tiers.writerProvider || 'openai';
  const writerTier = tiers.writer || 'premium';
  
  // API Key States
  const [apiKeys, setApiKeys] = useState({
    anthropic: '',
    openai: '',
    gemini: '',
    tavily: '',
  });
  const [showKeys, setShowKeys] = useState({
    anthropic: false,
    openai: false,
    gemini: false,
    tavily: false,
  });
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (open) {
      getSettings().then((data) => {
        setSettings(data);
        setStatus(data.api_status);
      });
    }
  }, [open]);
  
  const handleSaveKeys = async () => {
    setSaving(true);
    setSaveSuccess(false);
    try {
      const keysToSave: Record<string, string> = {};
      if (apiKeys.anthropic) keysToSave.anthropic = apiKeys.anthropic;
      if (apiKeys.openai) keysToSave.openai = apiKeys.openai;
      if (apiKeys.gemini) keysToSave.gemini = apiKeys.gemini;
      if (apiKeys.tavily) keysToSave.tavily = apiKeys.tavily;
      
      if (Object.keys(keysToSave).length > 0) {
        const result = await saveApiKeys(keysToSave);
        setSettings(result);
        setStatus(result.api_status);
        setApiKeys({ anthropic: '', openai: '', gemini: '', tavily: '' });
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 3000);
      }
    } finally {
      setSaving(false);
    }
  };

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

              {/* Writer - eigene Section mit Provider-Auswahl */}
              <div className="p-3 bg-neutral-50 rounded-lg border-2 border-blue-100">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-sm text-neutral-900">Writer</span>
                </div>
                <p className="text-xs text-neutral-500 mb-2">Schreibt den Artikel</p>
                
                {/* Provider Toggle */}
                <div className="flex gap-1 mb-2 p-1 bg-neutral-200 rounded">
                  <button
                    onClick={() => onWriterProviderChange?.('openai')}
                    className={`flex-1 py-1 text-xs rounded transition-colors ${
                      writerProvider === 'openai'
                        ? 'bg-white text-neutral-900 shadow-sm'
                        : 'text-neutral-500 hover:text-neutral-700'
                    }`}
                  >
                    OpenAI
                  </button>
                  <button
                    onClick={() => onWriterProviderChange?.('gemini')}
                    className={`flex-1 py-1 text-xs rounded transition-colors ${
                      writerProvider === 'gemini'
                        ? 'bg-white text-neutral-900 shadow-sm'
                        : 'text-neutral-500 hover:text-neutral-700'
                    }`}
                  >
                    Gemini
                  </button>
                </div>

                {/* Tier Buttons */}
                <div className="flex gap-2">
                  <button
                    onClick={() => onTierChange('writer', 'premium')}
                    className={`flex-1 py-1.5 text-xs rounded transition-colors flex flex-col items-center ${
                      writerTier === 'premium'
                        ? 'bg-neutral-900 text-white'
                        : 'bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-100'
                    }`}
                  >
                    <span className="font-medium">Premium</span>
                    <span className={`text-[10px] ${writerTier === 'premium' ? 'text-neutral-300' : 'text-neutral-400'}`}>
                      {writerModels[writerProvider].premium}
                    </span>
                  </button>
                  <button
                    onClick={() => onTierChange('writer', 'budget')}
                    className={`flex-1 py-1.5 text-xs rounded transition-colors flex flex-col items-center ${
                      writerTier === 'budget'
                        ? 'bg-neutral-900 text-white'
                        : 'bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-100'
                    }`}
                  >
                    <span className="font-medium">Budget</span>
                    <span className={`text-[10px] ${writerTier === 'budget' ? 'text-neutral-300' : 'text-neutral-400'}`}>
                      {writerModels[writerProvider].budget}
                    </span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* API Keys */}
          <div>
            <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3 flex items-center gap-2">
              <Key size={14} />
              API Keys
            </h3>
            <div className="space-y-3">
              {/* Anthropic */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-neutral-700">Anthropic (Claude)</label>
                  {status?.anthropic ? (
                    <span className="text-xs text-green-600 flex items-center gap-1"><Check size={12} /> Aktiv</span>
                  ) : (
                    <span className="text-xs text-red-500">Fehlt</span>
                  )}
                </div>
                <div className="relative">
                  <input
                    type={showKeys.anthropic ? 'text' : 'password'}
                    placeholder={settings?.api_keys.anthropic || 'sk-ant-...'}
                    value={apiKeys.anthropic}
                    onChange={(e) => setApiKeys({ ...apiKeys, anthropic: e.target.value })}
                    className="w-full text-xs p-2 pr-8 bg-neutral-50 border border-neutral-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowKeys({ ...showKeys, anthropic: !showKeys.anthropic })}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
                  >
                    {showKeys.anthropic ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>
              
              {/* OpenAI */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-neutral-700">OpenAI (GPT)</label>
                  {status?.openai ? (
                    <span className="text-xs text-green-600 flex items-center gap-1"><Check size={12} /> Aktiv</span>
                  ) : (
                    <span className="text-xs text-red-500">Fehlt</span>
                  )}
                </div>
                <div className="relative">
                  <input
                    type={showKeys.openai ? 'text' : 'password'}
                    placeholder={settings?.api_keys.openai || 'sk-...'}
                    value={apiKeys.openai}
                    onChange={(e) => setApiKeys({ ...apiKeys, openai: e.target.value })}
                    className="w-full text-xs p-2 pr-8 bg-neutral-50 border border-neutral-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowKeys({ ...showKeys, openai: !showKeys.openai })}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
                  >
                    {showKeys.openai ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>
              
              {/* Gemini */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-neutral-700">Google (Gemini)</label>
                  {status?.gemini ? (
                    <span className="text-xs text-green-600 flex items-center gap-1"><Check size={12} /> Aktiv</span>
                  ) : (
                    <span className="text-xs text-red-500">Fehlt</span>
                  )}
                </div>
                <div className="relative">
                  <input
                    type={showKeys.gemini ? 'text' : 'password'}
                    placeholder={settings?.api_keys.gemini || 'AIza...'}
                    value={apiKeys.gemini}
                    onChange={(e) => setApiKeys({ ...apiKeys, gemini: e.target.value })}
                    className="w-full text-xs p-2 pr-8 bg-neutral-50 border border-neutral-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowKeys({ ...showKeys, gemini: !showKeys.gemini })}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
                  >
                    {showKeys.gemini ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>
              
              {/* Tavily */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-neutral-700">Tavily (Web Search)</label>
                  {status?.tavily ? (
                    <span className="text-xs text-green-600 flex items-center gap-1"><Check size={12} /> Aktiv</span>
                  ) : (
                    <span className="text-xs text-red-500">Fehlt</span>
                  )}
                </div>
                <div className="relative">
                  <input
                    type={showKeys.tavily ? 'text' : 'password'}
                    placeholder={settings?.api_keys.tavily || 'tvly-...'}
                    value={apiKeys.tavily}
                    onChange={(e) => setApiKeys({ ...apiKeys, tavily: e.target.value })}
                    className="w-full text-xs p-2 pr-8 bg-neutral-50 border border-neutral-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowKeys({ ...showKeys, tavily: !showKeys.tavily })}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
                  >
                    {showKeys.tavily ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>
              
              {/* Save Button */}
              <button
                onClick={handleSaveKeys}
                disabled={saving || (!apiKeys.anthropic && !apiKeys.openai && !apiKeys.gemini && !apiKeys.tavily)}
                className={`w-full py-2 rounded text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
                  saveSuccess
                    ? 'bg-green-500 text-white'
                    : saving || (!apiKeys.anthropic && !apiKeys.openai && !apiKeys.gemini && !apiKeys.tavily)
                    ? 'bg-neutral-200 text-neutral-400 cursor-not-allowed'
                    : 'bg-blue-500 text-white hover:bg-blue-600'
                }`}
              >
                {saveSuccess ? (
                  <>
                    <Check size={16} />
                    Gespeichert!
                  </>
                ) : saving ? (
                  'Speichern...'
                ) : (
                  <>
                    <Save size={16} />
                    Keys speichern
                  </>
                )}
              </button>
              
              <p className="text-xs text-neutral-400 text-center">
                Keys werden sicher lokal gespeichert
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

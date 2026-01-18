import { X, Clock, Cpu, Coins, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import type { SessionLog } from '../lib/api';

interface LogDrawerProps {
  open: boolean;
  onClose: () => void;
  log: SessionLog | null;
  loading: boolean;
}

function formatDuration(ms: number | null): string {
  if (!ms) return '-';
  if (ms < 1000) return `${ms}ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = (seconds % 60).toFixed(0);
  return `${minutes}m ${remainingSeconds}s`;
}

function formatTokens(tokens: { input: number; output: number } | null): string {
  if (!tokens) return '-';
  return `${tokens.input.toLocaleString()} / ${tokens.output.toLocaleString()}`;
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'success':
    case 'completed':
      return <CheckCircle size={14} className="text-green-500" />;
    case 'error':
      return <XCircle size={14} className="text-red-500" />;
    case 'aborted':
      return <AlertCircle size={14} className="text-yellow-500" />;
    default:
      return <Clock size={14} className="text-neutral-400" />;
  }
}

export function LogDrawer({ open, onClose, log, loading }: LogDrawerProps) {
  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed top-0 right-0 h-full w-[500px] bg-white shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-neutral-200">
          <h2 className="font-semibold text-neutral-900">Session Log</h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-neutral-100 text-neutral-500"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin w-6 h-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full" />
            </div>
          ) : !log ? (
            <div className="text-center text-neutral-500 py-12">
              Kein Log verfügbar für diesen Artikel
            </div>
          ) : (
            <div className="space-y-6">
              {/* Summary */}
              {log.summary && (
                <div className="bg-neutral-50 rounded-lg p-4">
                  <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
                    Zusammenfassung
                  </h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex items-center gap-2">
                      <Clock size={16} className="text-neutral-400" />
                      <div>
                        <div className="text-xs text-neutral-500">Dauer</div>
                        <div className="font-medium">{formatDuration(log.summary.total_duration_ms)}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Cpu size={16} className="text-neutral-400" />
                      <div>
                        <div className="text-xs text-neutral-500">Tokens (In/Out)</div>
                        <div className="font-medium">{formatTokens(log.summary.total_tokens)}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Coins size={16} className="text-neutral-400" />
                      <div>
                        <div className="text-xs text-neutral-500">Geschätzte Kosten</div>
                        <div className="font-medium">${log.summary.estimated_cost_usd.toFixed(4)}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <CheckCircle size={16} className="text-neutral-400" />
                      <div>
                        <div className="text-xs text-neutral-500">Schritte</div>
                        <div className="font-medium">
                          {log.summary.steps_completed} OK
                          {log.summary.steps_failed > 0 && (
                            <span className="text-red-500 ml-1">/ {log.summary.steps_failed} Fehler</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Settings */}
              <div>
                <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
                  Einstellungen
                </h3>
                <div className="bg-neutral-50 rounded-lg p-3 text-sm">
                  <div className="flex justify-between py-1">
                    <span className="text-neutral-500">Recherche-Runden</span>
                    <span className="font-medium">{log.settings.research_rounds}</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-neutral-500">Editor</span>
                    <span className="font-medium">{log.settings.use_editor ? 'Ja' : 'Nein'}</span>
                  </div>
                  {Object.entries(log.settings.tiers).length > 0 && (
                    <div className="pt-2 mt-2 border-t border-neutral-200">
                      <div className="text-xs text-neutral-400 mb-1">Modell-Tiers</div>
                      {Object.entries(log.settings.tiers).map(([agent, tier]) => (
                        <div key={agent} className="flex justify-between py-0.5">
                          <span className="text-neutral-500 capitalize">{agent}</span>
                          <span className={`text-xs px-1.5 py-0.5 rounded ${
                            tier === 'premium' ? 'bg-amber-100 text-amber-700' : 'bg-neutral-200 text-neutral-600'
                          }`}>
                            {tier}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Timeline */}
              <div>
                <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
                  Timeline ({log.timeline.length} Schritte)
                </h3>
                <div className="space-y-2">
                  {log.timeline.map((step, index) => (
                    <div
                      key={index}
                      className={`p-3 rounded-lg border ${
                        step.status === 'error' ? 'border-red-200 bg-red-50' :
                        step.status === 'aborted' ? 'border-yellow-200 bg-yellow-50' :
                        'border-neutral-200 bg-white'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <StatusIcon status={step.status} />
                          <span className="font-medium text-sm">{step.agent}</span>
                          <span className="text-xs text-neutral-400">{step.action}</span>
                        </div>
                        <span className="text-xs text-neutral-400">
                          {formatDuration(step.duration_ms)}
                        </span>
                      </div>
                      
                      <div className="text-xs text-neutral-500 mb-2">
                        <span className="px-1.5 py-0.5 bg-neutral-100 rounded mr-2">{step.model}</span>
                        <span className="text-neutral-400">{step.provider}</span>
                      </div>

                      <div className="text-xs text-neutral-600 line-clamp-2 mb-2">
                        {step.task}
                      </div>

                      <div className="flex items-center gap-4 text-xs text-neutral-400">
                        {step.tokens && (
                          <span>Tokens: {step.tokens.input}/{step.tokens.output}</span>
                        )}
                        {step.tool_calls.length > 0 && (
                          <span>Tools: {step.tool_calls.join(', ')}</span>
                        )}
                        {step.result_length && (
                          <span>{step.result_length.toLocaleString()} Zeichen</span>
                        )}
                      </div>

                      {step.error && (
                        <div className="mt-2 text-xs text-red-600 bg-red-100 rounded p-2">
                          {step.error}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

import { X, Clock, Cpu, Coins, CheckCircle, XCircle, AlertCircle, Wrench } from 'lucide-react';
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
                  {log.settings.mode && (
                    <div className="flex justify-between py-1">
                      <span className="text-neutral-500">Modus</span>
                      <span className="font-medium">
                        {log.settings.mode === 'evidence_gated' ? 'Evidence-Gated' : log.settings.mode}
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between py-1">
                    <span className="text-neutral-500">Recherche</span>
                    <span className="font-medium">
                      {typeof log.settings.research_rounds === 'string' 
                        ? log.settings.research_rounds 
                        : `${log.settings.research_rounds} Runden`}
                    </span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-neutral-500">Editor</span>
                    <span className="font-medium">{log.settings.use_editor ? 'Ja' : 'Nein'}</span>
                  </div>
                  {/* Verwendete Modelle aus Timeline extrahieren */}
                  {log.timeline && log.timeline.length > 0 && (
                    <div className="pt-2 mt-2 border-t border-neutral-200">
                      <div className="text-xs text-neutral-400 mb-2">Verwendete Modelle</div>
                      {(() => {
                        // Einzigartige Agent→Modell-Kombinationen extrahieren
                        const modelsByAgent = new Map<string, { model: string; provider: string; tokens: { input: number; output: number } }>();
                        log.timeline.forEach(step => {
                          if (step.model && step.model !== 'tool-based') {
                            const existing = modelsByAgent.get(step.agent);
                            if (existing) {
                              // Tokens akkumulieren
                              if (step.tokens) {
                                existing.tokens.input += step.tokens.input;
                                existing.tokens.output += step.tokens.output;
                              }
                            } else {
                              modelsByAgent.set(step.agent, {
                                model: step.model,
                                provider: step.provider,
                                tokens: step.tokens ? { ...step.tokens } : { input: 0, output: 0 }
                              });
                            }
                          }
                        });
                        return Array.from(modelsByAgent.entries()).map(([agent, info]) => (
                          <div key={agent} className="py-1.5 border-b border-neutral-100 last:border-0">
                            <div className="flex justify-between items-center">
                              <span className="text-neutral-700 font-medium text-xs">{agent}</span>
                              <span className="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded">
                                {info.model}
                              </span>
                            </div>
                            <div className="flex justify-between items-center mt-0.5">
                              <span className="text-neutral-400 text-xs">{info.provider}</span>
                              {info.tokens.input > 0 && (
                                <span className="text-neutral-400 text-xs">
                                  {(info.tokens.input / 1000).toFixed(1)}k / {(info.tokens.output / 1000).toFixed(1)}k tok
                                </span>
                              )}
                            </div>
                          </div>
                        ));
                      })()}
                    </div>
                  )}
                </div>
              </div>

              {/* Timeline */}
              <div>
                <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
                  Timeline ({log.timeline.length} Schritte)
                </h3>
                <div className="space-y-3">
                  {log.timeline.map((step, index) => (
                    <div
                      key={index}
                      className={`p-3 rounded-lg border ${
                        step.status === 'error' ? 'border-red-200 bg-red-50' :
                        step.status === 'aborted' ? 'border-yellow-200 bg-yellow-50' :
                        'border-neutral-200 bg-white'
                      }`}
                    >
                      {/* Header: Agent, Action, Duration */}
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <StatusIcon status={step.status} />
                          <span className="font-medium text-sm">{step.agent}</span>
                          <span className="text-xs px-1.5 py-0.5 bg-neutral-100 text-neutral-500 rounded">
                            {step.action}
                          </span>
                        </div>
                        <span className="text-xs font-medium text-neutral-500">
                          {formatDuration(step.duration_ms)}
                        </span>
                      </div>
                      
                      {/* Model & Provider */}
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded">
                          {step.model}
                        </span>
                        <span className="text-xs text-neutral-400">{step.provider}</span>
                        {step.tokens && (
                          <span className="text-xs text-neutral-400 ml-auto">
                            {step.tokens.input.toLocaleString()} → {step.tokens.output.toLocaleString()} tok
                          </span>
                        )}
                      </div>

                      {/* Tools verwendet */}
                      {step.tool_calls && step.tool_calls.length > 0 && (
                        <div className="flex items-center gap-2 mb-2">
                          <Wrench size={12} className="text-neutral-400" />
                          <div className="flex flex-wrap gap-1">
                            {step.tool_calls.map((tool, i) => (
                              <span key={i} className="text-xs px-1.5 py-0.5 bg-amber-50 text-amber-700 rounded">
                                {tool}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Task Description */}
                      <div className="text-xs text-neutral-600 mb-2">
                        {step.task}
                      </div>

                      {/* Details Grid */}
                      {step.details && Object.keys(step.details).length > 0 && (
                        <div className="bg-neutral-50 rounded p-2 mt-2">
                          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                            {Object.entries(step.details).map(([key, value]) => (
                              <div key={key} className="flex justify-between text-xs">
                                <span className="text-neutral-500">
                                  {key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                </span>
                                <span className="font-medium text-neutral-700">
                                  {Array.isArray(value) 
                                    ? value.join(', ') 
                                    : typeof value === 'number' 
                                      ? value.toLocaleString()
                                      : String(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Result Length */}
                      {step.result_length && !step.details && (
                        <div className="text-xs text-neutral-400 mt-1">
                          Ergebnis: {step.result_length.toLocaleString()} Zeichen
                        </div>
                      )}

                      {/* Error */}
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

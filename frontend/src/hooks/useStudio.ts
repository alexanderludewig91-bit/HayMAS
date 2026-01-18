import { useState, useCallback, useRef } from 'react';
import type { StudioState, AgentEvent, AgentTiers, Article, ResearchPlan, ResearchRound } from '../types';
import { generateArticle, getArticle, analyzeTopic } from '../lib/api';

interface StudioStore {
  // State
  state: StudioState;
  question: string;
  events: AgentEvent[];
  articleContent: string | null;
  articlePath: string | null;
  error: string | null;

  // Research Plan
  plan: ResearchPlan | null;
  isAnalyzing: boolean;

  // UI
  archiveOpen: boolean;
  settingsOpen: boolean;

  // Settings
  tiers: AgentTiers;

  // Actions
  setQuestion: (q: string) => void;
  analyzeAndPlan: () => Promise<void>;
  updatePlan: (plan: ResearchPlan) => void;
  updateRound: (index: number, round: Partial<ResearchRound>) => void;
  toggleRound: (index: number) => void;
  setUseEditor: (use: boolean) => void;
  startGeneration: () => void;
  startGenerationWithoutPlan: () => void;
  cancelGeneration: () => void;
  reset: () => void;
  loadArticle: (article: Article) => void;
  setArchiveOpen: (open: boolean) => void;
  setSettingsOpen: (open: boolean) => void;
  setTier: (agent: keyof AgentTiers, tier: 'premium' | 'budget') => void;
}

export function useStudio(): StudioStore {
  const [state, setState] = useState<StudioState>('idle');
  const [question, setQuestion] = useState('');
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [articleContent, setArticleContent] = useState<string | null>(null);
  const [articlePath, setArticlePath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Research Plan State
  const [plan, setPlan] = useState<ResearchPlan | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const [archiveOpen, setArchiveOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const [tiers, setTiers] = useState<AgentTiers>({
    orchestrator: 'premium',
    researcher: 'premium',
    writer: 'premium',
    editor: 'premium',
  });

  const cancelRef = useRef<(() => void) | null>(null);

  // Thema analysieren und Plan erstellen
  const analyzeAndPlan = useCallback(async () => {
    if (!question.trim()) return;

    setIsAnalyzing(true);
    setState('analyzing');
    setError(null);

    try {
      const response = await analyzeTopic(question);
      if (response.success && response.plan) {
        setPlan(response.plan);
        
        // NEU: Modell-Empfehlungen übernehmen (wenn vorhanden)
        if (response.plan.model_recommendations) {
          const recs = response.plan.model_recommendations;
          setTiers({
            orchestrator: recs.orchestrator || 'premium',
            researcher: recs.researcher || 'premium',
            writer: recs.writer || 'premium',
            editor: recs.editor || 'premium',
          });
        }
        
        setState('planning');
      } else {
        setError('Analyse fehlgeschlagen');
        setState('idle');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analyse fehlgeschlagen');
      setState('idle');
    } finally {
      setIsAnalyzing(false);
    }
  }, [question]);

  // Plan aktualisieren
  const updatePlan = useCallback((newPlan: ResearchPlan) => {
    setPlan(newPlan);
  }, []);

  // Einzelne Runde aktualisieren
  const updateRound = useCallback((index: number, updates: Partial<ResearchRound>) => {
    setPlan((prev) => {
      if (!prev) return prev;
      const newRounds = [...prev.rounds];
      newRounds[index] = { ...newRounds[index], ...updates };
      return { ...prev, rounds: newRounds };
    });
  }, []);

  // Runde aktivieren/deaktivieren
  const toggleRound = useCallback((index: number) => {
    setPlan((prev) => {
      if (!prev) return prev;
      const newRounds = [...prev.rounds];
      newRounds[index] = { ...newRounds[index], enabled: !newRounds[index].enabled };
      return { ...prev, rounds: newRounds };
    });
  }, []);

  // Editor-Option setzen
  const setUseEditor = useCallback((use: boolean) => {
    setPlan((prev) => {
      if (!prev) return prev;
      return { ...prev, use_editor: use };
    });
  }, []);

  // Generierung mit Plan starten
  const startGeneration = useCallback(() => {
    if (!question.trim()) return;

    setState('producing');
    setEvents([]);
    setArticleContent(null);
    setArticlePath(null);
    setError(null);

    const cancel = generateArticle(
      question,
      tiers,
      plan || undefined,
      (event) => {
        setEvents((prev) => [...prev, event]);

        // Check for article path in response
        if (event.type === 'response' && event.data?.article_path) {
          setArticlePath(event.data.article_path as string);
        }
      },
      async () => {
        // Done - fetch article content
        setState('complete');
        // Artikel laden nach kurzer Verzögerung
        setTimeout(async () => {
          const lastEvent = events[events.length - 1];
          if (lastEvent?.data?.article_path) {
            const filename = (lastEvent.data.article_path as string).split('/').pop();
            if (filename) {
              try {
                const content = await getArticle(filename);
                setArticleContent(content);
              } catch {
                // Ignore
              }
            }
          }
        }, 100);
      },
      (err) => {
        setError(err);
        setState('idle');
      }
    );

    cancelRef.current = cancel;
  }, [question, tiers, plan, events]);

  // Generierung ohne Plan starten (Auto-Modus)
  const startGenerationWithoutPlan = useCallback(() => {
    if (!question.trim()) return;

    setState('producing');
    setEvents([]);
    setArticleContent(null);
    setArticlePath(null);
    setError(null);
    setPlan(null);

    const cancel = generateArticle(
      question,
      tiers,
      undefined, // Kein Plan → Orchestrator analysiert selbst
      (event) => {
        setEvents((prev) => [...prev, event]);

        if (event.type === 'response' && event.data?.article_path) {
          setArticlePath(event.data.article_path as string);
        }
      },
      async () => {
        setState('complete');
        setTimeout(async () => {
          const lastEvent = events[events.length - 1];
          if (lastEvent?.data?.article_path) {
            const filename = (lastEvent.data.article_path as string).split('/').pop();
            if (filename) {
              try {
                const content = await getArticle(filename);
                setArticleContent(content);
              } catch {
                // Ignore
              }
            }
          }
        }, 100);
      },
      (err) => {
        setError(err);
        setState('idle');
      }
    );

    cancelRef.current = cancel;
  }, [question, tiers, events]);

  const cancelGeneration = useCallback(() => {
    cancelRef.current?.();
    setState('idle');
  }, []);

  const reset = useCallback(() => {
    setState('idle');
    setQuestion('');
    setEvents([]);
    setArticleContent(null);
    setArticlePath(null);
    setError(null);
    setPlan(null);
  }, []);

  const loadArticle = useCallback(async (article: Article) => {
    try {
      const content = await getArticle(article.filename);
      setArticleContent(content);
      setArticlePath(article.filename);
      setState('complete');
      setArchiveOpen(false);
    } catch {
      setError('Artikel konnte nicht geladen werden');
    }
  }, []);

  const setTier = useCallback((agent: keyof AgentTiers, tier: 'premium' | 'budget') => {
    setTiers((prev) => ({ ...prev, [agent]: tier }));
  }, []);

  return {
    state,
    question,
    events,
    articleContent,
    articlePath,
    error,
    plan,
    isAnalyzing,
    archiveOpen,
    settingsOpen,
    tiers,
    setQuestion,
    analyzeAndPlan,
    updatePlan,
    updateRound,
    toggleRound,
    setUseEditor,
    startGeneration,
    startGenerationWithoutPlan,
    cancelGeneration,
    reset,
    loadArticle,
    setArchiveOpen,
    setSettingsOpen,
    setTier,
  };
}

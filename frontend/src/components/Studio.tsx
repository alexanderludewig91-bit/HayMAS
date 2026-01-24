import { useState } from 'react';
import { useStudio } from '../hooks/useStudio';
import { Header } from './Header';
import { IdleView } from './IdleView';
import { PlanningView } from './PlanningView';
import { ProducingView } from './ProducingView';
import { CompleteView } from './CompleteView';
import { ArchiveDrawer } from './ArchiveDrawer';
import { SettingsDrawer } from './SettingsDrawer';
import { PromptRefiner } from './PromptRefiner';

export function Studio() {
  const {
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
  } = useStudio();

  // Prompt Refiner Modal State
  const [refinerOpen, setRefinerOpen] = useState(false);
  const [refinerMode, setRefinerMode] = useState<'analyze' | 'quickstart'>('analyze');

  // Öffnet den Refiner statt direkt zu starten
  const handleAnalyzeClick = () => {
    if (question.trim()) {
      setRefinerMode('analyze');
      setRefinerOpen(true);
    }
  };

  const handleQuickStartClick = () => {
    if (question.trim()) {
      setRefinerMode('quickstart');
      setRefinerOpen(true);
    }
  };

  // Callback wenn Refiner bestätigt wird
  const handleRefinerConfirm = (optimizedPrompt: string, _parameters: { target_pages: number; audience: string; tone: string; format: string }) => {
    setRefinerOpen(false);
    // Optimierten Prompt übernehmen
    setQuestion(optimizedPrompt);
    
    // Je nach Modus weitermachen
    if (refinerMode === 'analyze') {
      // Kurze Verzögerung damit der State aktualisiert wird
      setTimeout(() => {
        analyzeAndPlan();
      }, 50);
    } else {
      setTimeout(() => {
        startGenerationWithoutPlan();
      }, 50);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-50 flex flex-col">
      <Header
        onArchiveClick={() => setArchiveOpen(true)}
        onSettingsClick={() => setSettingsOpen(true)}
      />

      {/* Main Content - below header */}
      <main className="flex-1 flex flex-col pt-14">
        {error && (
          <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {(state === 'idle' || state === 'analyzing') && (
          <IdleView
            question={question}
            onQuestionChange={setQuestion}
            onAnalyze={handleAnalyzeClick}
            onQuickStart={handleQuickStartClick}
            isAnalyzing={isAnalyzing}
          />
        )}

        {state === 'planning' && plan && (
          <PlanningView
            question={question}
            plan={plan}
            tiers={tiers}
            onUpdatePlan={updatePlan}
            onToggleRound={toggleRound}
            onUpdateRound={updateRound}
            onSetUseEditor={setUseEditor}
            onSetTier={setTier}
            onStart={startGeneration}
            onBack={reset}
          />
        )}

        {state === 'producing' && (
          <ProducingView
            question={question}
            events={events}
            onCancel={cancelGeneration}
          />
        )}

        {state === 'complete' && (
          <CompleteView
            articleContent={articleContent}
            articlePath={articlePath}
            onReset={reset}
          />
        )}
      </main>

      {/* Drawers */}
      <ArchiveDrawer
        open={archiveOpen}
        onClose={() => setArchiveOpen(false)}
        onSelectArticle={loadArticle}
      />

      <SettingsDrawer
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        tiers={tiers}
        onTierChange={setTier}
      />

      {/* Prompt Refiner Modal */}
      <PromptRefiner
        isOpen={refinerOpen}
        originalPrompt={question}
        onClose={() => setRefinerOpen(false)}
        onConfirm={handleRefinerConfirm}
      />
    </div>
  );
}

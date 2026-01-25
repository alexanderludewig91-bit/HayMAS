import { useState } from 'react';
import { useStudio } from '../hooks/useStudio';
import { Header } from './Header';
import { IdleView } from './IdleView';
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
    isAnalyzing,
    archiveOpen,
    settingsOpen,
    tiers,
    setQuestion,
    startGenerationWithoutPlan,
    cancelGeneration,
    viewArticle,
    reset,
    loadArticle,
    setArchiveOpen,
    setSettingsOpen,
    setTier,
  } = useStudio();

  // Prompt Refiner Modal State
  const [refinerOpen, setRefinerOpen] = useState(false);

  // Öffnet den Refiner vor dem Start
  const handleStartClick = () => {
    if (question.trim()) {
      setRefinerOpen(true);
    }
  };

  // Callback wenn Refiner bestätigt wird
  const handleRefinerConfirm = (optimizedPrompt: string, parameters: { target_pages: number; audience: string; tone: string; format: string }) => {
    setRefinerOpen(false);
    // Optimierten Prompt übernehmen
    setQuestion(optimizedPrompt);
    
    // Direkt starten mit gewähltem Format (Evidence-Gated Workflow)
    setTimeout(() => {
      startGenerationWithoutPlan(parameters.format);
    }, 50);
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
            onStart={handleStartClick}
            isGenerating={isAnalyzing}
          />
        )}

        {(state === 'producing' || state === 'finished') && (
          <ProducingView
            question={question}
            events={events}
            onCancel={cancelGeneration}
            isFinished={state === 'finished'}
            onViewArticle={viewArticle}
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

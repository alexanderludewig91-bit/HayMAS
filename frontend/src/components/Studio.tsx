import { useStudio } from '../hooks/useStudio';
import { Header } from './Header';
import { IdleView } from './IdleView';
import { PlanningView } from './PlanningView';
import { ProducingView } from './ProducingView';
import { CompleteView } from './CompleteView';
import { ArchiveDrawer } from './ArchiveDrawer';
import { SettingsDrawer } from './SettingsDrawer';

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
            onAnalyze={analyzeAndPlan}
            onQuickStart={startGenerationWithoutPlan}
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
    </div>
  );
}

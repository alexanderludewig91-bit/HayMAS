export type StudioState = 'idle' | 'analyzing' | 'planning' | 'producing' | 'complete';

export type EventType = 'thinking' | 'tool_call' | 'tool_result' | 'response' | 'error' | 'status';

export interface AgentEvent {
  type: EventType;
  agent: string;
  content: string;
  data?: Record<string, unknown>;
}

export interface Article {
  filename: string;
  title: string;
  modified: string;
  size: number;
}

export interface ApiStatus {
  anthropic: boolean;
  openai: boolean;
  gemini: boolean;
  tavily: boolean;
}

export type Tier = 'premium' | 'budget';

export interface AgentTiers {
  orchestrator: Tier;
  researcher: Tier;
  writer: Tier;
  editor: Tier;
}

// ============================================================================
// RESEARCH PLAN TYPES
// ============================================================================

export type ResearchTool = 'tavily' | 'wikipedia' | 'gnews' | 'hackernews' | 'semantic_scholar' | 'arxiv' | 'ted';

export interface ResearchRound {
  name: string;
  focus: string;
  search_query: string;
  tool: ResearchTool;  // NEU: Welches Tool für diese Runde
  enabled: boolean;
}

export interface ModelRecommendations {
  orchestrator: Tier;
  researcher: Tier;
  writer: Tier;
  editor: Tier;
}

export interface ResearchPlan {
  topic_type: string;
  time_relevance: string;
  needs_current_data: boolean;
  geographic_focus: string;
  complexity: string;
  rounds: ResearchRound[];
  use_editor: boolean;
  reasoning: string;
  model_recommendations?: ModelRecommendations;  // NEU: Modell-Empfehlungen
}

export interface AnalyzeResponse {
  success: boolean;
  plan: ResearchPlan;
  events: AgentEvent[];
  estimated_cost?: number;  // NEU: Geschätzte Kosten
}

// Research Tool Info (von der API)
export interface ResearchToolInfo {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  is_free: boolean;
  best_for: string[];
  topic_types: string[];
}

// ============================================================================
// EDITOR VERDICT TYPES (Smart Editor-Routing)
// ============================================================================

export type EditorVerdictType = 'approved' | 'revise' | 'research';
export type EditorIssueType = 'style' | 'structure' | 'content_gap' | 'factual_error';
export type IssueSeverity = 'minor' | 'major' | 'critical';

export interface EditorIssue {
  type: EditorIssueType;
  description: string;
  severity: IssueSeverity;
  suggested_action: 'revise' | 'research';
  research_query?: string;
}

export interface EditorVerdict {
  verdict: EditorVerdictType;
  confidence: number;
  issues: EditorIssue[];
  summary: string;
  raw_feedback: string;
}

export interface OrchestratorDecision {
  action: 'approved' | 'revise' | 'research';
  research_rounds: ResearchRound[];
  reasoning: string;
}

// Legacy - wird noch für Rückwärtskompatibilität gebraucht
export interface GenerationOptions {
  researchRounds: number;  // 1-5
  useEditor: boolean;
}

export type DashboardStats = {
  profile_completion: number;
  applications: number;
  resume_versions: number;
  match_score_history: number[];
  upcoming_interviews: number;
  average_match_score: number;
};

export type MatchResult = {
  score: number;
  missing_skills: string[];
  strengths: string[];
  weaknesses: string[];
  reasoning: string;
};

export type InterviewQuestion = {
  kind: string;
  question: string;
  ideal_answer: string;
};

export type ResumeOptimization = {
  optimized_resume: string;
  improved_bullets: string[];
  summary: string;
  confidence: number;
};

export type CareerSuggestions = {
  suggestions: string[];
  upskill_plan: string[];
  networking_tips: string[];
  confidence: number;
};

export type ApplicationItem = {
  id: number;
  company: string;
  role: string;
  date_applied: string;
  status: string;
  notes: string;
};

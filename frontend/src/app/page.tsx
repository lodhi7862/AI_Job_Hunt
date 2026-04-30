"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";

import { DashboardCard } from "@/components/dashboard-card";
import api from "@/lib/api";
import { ApplicationItem, CareerSuggestions, DashboardStats, InterviewQuestion, MatchResult, ResumeOptimization } from "@/lib/types";

const defaultStats: DashboardStats = {
  profile_completion: 0,
  applications: 0,
  resume_versions: 0,
  match_score_history: [],
  upcoming_interviews: 0,
  average_match_score: 0,
};

export default function Home() {
  const [stats, setStats] = useState<DashboardStats>(defaultStats);
  const [email, setEmail] = useState("demo@copilot.ai");
  const [password, setPassword] = useState("Password123!");
  const [jobDescription, setJobDescription] = useState("");
  const [jobId, setJobId] = useState<number | null>(null);
  const [resumeId, setResumeId] = useState<number | null>(null);
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);
  const [coverLetter, setCoverLetter] = useState("");
  const [applicationEmail, setApplicationEmail] = useState<{ email: string; subject: string; body: string } | null>(null);
  const [interviewQuestions, setInterviewQuestions] = useState<InterviewQuestion[]>([]);
  const [resumeOptimization, setResumeOptimization] = useState<ResumeOptimization | null>(null);
  const [careerSuggestions, setCareerSuggestions] = useState<CareerSuggestions | null>(null);
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [trackerCompany, setTrackerCompany] = useState("");
  const [trackerRole, setTrackerRole] = useState("");
  const [aiConfigured, setAiConfigured] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);

  const loadDashboard = async () => {
    try {
      const response = await api.get("/dashboard");
      setStats(response.data);
    } catch {
      // Not authenticated yet.
    }
  };

  useEffect(() => {
    const id = setTimeout(() => {
      void loadDashboard();
    }, 0);
    return () => clearTimeout(id);
  }, []);

  useEffect(() => {
    const loadAIStatus = async () => {
      try {
        const response = await api.get("/ai/status");
        setAiConfigured(Boolean(response.data.configured));
      } catch {
        setAiConfigured(null);
      }
    };
    void loadAIStatus();
  }, []);

  const registerOrLogin = async () => {
    setBusy(true);
    try {
      const register = await api.post("/auth/register", {
        email,
        full_name: "Demo User",
        password,
      });
      localStorage.setItem("token", register.data.access_token);
      toast.success("Registered and logged in");
      await loadDashboard();
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 400) {
        try {
          const login = await api.post("/auth/login", { email, password });
          localStorage.setItem("token", login.data.access_token);
          toast.success("Logged in");
          await loadDashboard();
        } catch {
          toast.error("Authentication failed");
        }
      } else {
        toast.error("Registration failed");
      }
    } finally {
      setBusy(false);
    }
  };

  const uploadResume = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) {
      return;
    }
    const data = new FormData();
    data.append("file", e.target.files[0]);
    try {
      setBusy(true);
      const response = await api.post("/resumes/upload", data);
      setResumeId(response.data.resume_id);
      toast.success("Resume parsed successfully");
      await loadDashboard();
    } catch {
      toast.error("Resume upload failed");
    } finally {
      setBusy(false);
    }
  };

  const analyzeJob = async () => {
    if (jobDescription.trim().length < 50) {
      toast.error("Job description is too short");
      return;
    }
    try {
      setBusy(true);
      const response = await api.post("/jobs/analyze", {
        title: "Software Engineer",
        company: "Target Company",
        description: jobDescription,
      });
      setJobId(response.data.job_id);
      toast.success("Job analyzed");
    } catch {
      toast.error("Job analysis failed");
    } finally {
      setBusy(false);
    }
  };

  const runMatch = async () => {
    if (!resumeId || !jobId) {
      toast.error("Upload resume and analyze job first");
      return;
    }
    try {
      setBusy(true);
      const response = await api.post(`/match/${resumeId}/${jobId}`);
      setMatchResult(response.data);
      toast.success("Match generated");
      await loadDashboard();
    } catch {
      toast.error("Failed to generate match score");
    } finally {
      setBusy(false);
    }
  };

  const generateAiOutputs = async () => {
    if (!resumeId || !jobId) {
      toast.error("Upload resume and analyze job first");
      return;
    }
    try {
      setBusy(true);
      const [coverLetterRes, interviewRes, optimizeRes, careerRes] = await Promise.all([
        api.post(`/cover-letter/${jobId}/${resumeId}`),
        api.post(`/interview/${jobId}`),
        api.post(`/resume-optimize/${jobId}/${resumeId}`),
        api.post(`/career-suggestions/${jobId}/${resumeId}`),
      ]);
      setCoverLetter(coverLetterRes.data.cover_letter ?? "");
      setInterviewQuestions(interviewRes.data.questions ?? []);
      setResumeOptimization(optimizeRes.data);
      setCareerSuggestions(careerRes.data);
      toast.success("Generated full AI pack");
    } catch {
      toast.error("Failed to generate one or more AI sections");
    } finally {
      setBusy(false);
    }
  };

  const generateApplicationEmail = async () => {
    if (!resumeId || !jobId) {
      toast.error("Upload resume and analyze job first");
      return;
    }
    try {
      setBusy(true);
      const response = await api.post(`/application-email/${jobId}/${resumeId}`);
      setApplicationEmail(response.data);
      toast.success("Short application email generated");
    } catch {
      toast.error("Failed to generate application email");
    } finally {
      setBusy(false);
    }
  };

  const loadApplications = async () => {
    try {
      const response = await api.get("/applications");
      setApplications(response.data ?? []);
    } catch {
      toast.error("Failed to load application tracker");
    }
  };

  const createApplication = async () => {
    if (!trackerCompany.trim() || !trackerRole.trim()) {
      toast.error("Company and role are required");
      return;
    }
    try {
      setBusy(true);
      await api.post("/applications", {
        company: trackerCompany,
        role: trackerRole,
        date_applied: new Date().toISOString().slice(0, 10),
        status: "Applied",
        notes: "",
      });
      setTrackerCompany("");
      setTrackerRole("");
      await loadApplications();
      await loadDashboard();
      toast.success("Application added");
    } catch {
      toast.error("Failed to add application");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-8 md:px-8">
      <section className="rounded-2xl border border-white/10 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 p-6">
        <h1 className="text-3xl font-bold">AI Job Hunt Copilot</h1>
        <p className="mt-2 text-zinc-300">
          Optimize resumes, generate cover letters, score job fit, and track applications in one AI-powered workspace.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <DashboardCard label="Profile Completion" value={`${stats.profile_completion}%`} />
        <DashboardCard label="Applications" value={stats.applications} />
        <DashboardCard label="Resume Versions" value={stats.resume_versions} />
      </section>

      <section className="grid gap-4 rounded-xl border border-white/10 bg-zinc-900/80 p-4 md:grid-cols-2">
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">Authentication</h2>
          <input className="w-full rounded-md border border-zinc-700 bg-zinc-950 p-2" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input className="w-full rounded-md border border-zinc-700 bg-zinc-950 p-2" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <button className="rounded-md bg-indigo-600 px-4 py-2 font-medium hover:bg-indigo-500 disabled:opacity-60" disabled={busy} onClick={registerOrLogin}>
            {busy ? "Processing..." : "Register / Login"}
          </button>
          <input type="file" accept=".pdf,.docx" onChange={uploadResume} />
          <button className="rounded-md bg-sky-600 px-4 py-2 hover:bg-sky-500 disabled:opacity-60" disabled={busy} onClick={loadApplications}>
            Refresh Application Tracker
          </button>
        </div>
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">Job Description Analyzer</h2>
          <textarea
            className="min-h-40 w-full rounded-md border border-zinc-700 bg-zinc-950 p-2"
            placeholder="Paste job description..."
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
          />
          <div className="flex gap-2">
            <button className="rounded-md bg-emerald-600 px-4 py-2 hover:bg-emerald-500 disabled:opacity-60" disabled={busy} onClick={analyzeJob}>
              Analyze JD
            </button>
            <button className="rounded-md bg-fuchsia-600 px-4 py-2 hover:bg-fuchsia-500 disabled:opacity-60" disabled={busy} onClick={runMatch}>
              Run Match Engine
            </button>
            <button className="rounded-md bg-amber-600 px-4 py-2 hover:bg-amber-500 disabled:opacity-60" disabled={busy} onClick={generateAiOutputs}>
              Generate AI Pack
            </button>
            <button className="rounded-md bg-cyan-600 px-4 py-2 hover:bg-cyan-500 disabled:opacity-60" disabled={busy} onClick={generateApplicationEmail}>
              Short Apply Email
            </button>
          </div>
        </div>
      </section>

      {aiConfigured === false && (
        <section className="rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-red-200">
          AI provider is not configured. Set `DEEPSEEK_API_KEY` in `backend/.env`, then restart backend.
        </section>
      )}

      {matchResult && (
        <section className="rounded-xl border border-white/10 bg-zinc-900/80 p-4">
          <h2 className="text-xl font-semibold">Match Result</h2>
          <p className="mt-2 text-lg">Score: {matchResult.score}/100</p>
          <p className="mt-2 text-zinc-300">{matchResult.reasoning}</p>
          <p className="mt-2 text-zinc-300">Missing skills: {matchResult.missing_skills.join(", ") || "None"}</p>
          <p className="mt-2 text-zinc-300">Strengths: {matchResult.strengths.join(", ") || "None"}</p>
          <p className="mt-2 text-zinc-300">Weaknesses: {matchResult.weaknesses.join(", ") || "None"}</p>
        </section>
      )}

      {resumeOptimization && (
        <section className="rounded-xl border border-white/10 bg-zinc-900/80 p-4">
          <h2 className="text-xl font-semibold">ATS Optimized Resume</h2>
          <p className="mt-2 text-zinc-300">Confidence: {Math.round(resumeOptimization.confidence * 100)}%</p>
          <p className="mt-2 whitespace-pre-wrap text-zinc-200">{resumeOptimization.summary}</p>
          <ul className="mt-2 space-y-1 text-zinc-300">
            {resumeOptimization.improved_bullets.map((item, idx) => (
              <li key={`bullet-${idx}`}>- {item}</li>
            ))}
          </ul>
        </section>
      )}

      {coverLetter && (
        <section className="rounded-xl border border-white/10 bg-zinc-900/80 p-4">
          <h2 className="text-xl font-semibold">Tailored Cover Letter</h2>
          <p className="mt-2 whitespace-pre-wrap text-zinc-200">{coverLetter}</p>
        </section>
      )}

      {applicationEmail && (
        <section className="rounded-xl border border-white/10 bg-zinc-900/80 p-4">
          <h2 className="text-xl font-semibold">Short Apply-by-Email Draft</h2>
          <p className="mt-2 text-zinc-300">
            To: {applicationEmail.email || "No email found in job description"}
          </p>
          <p className="mt-2 text-zinc-200">
            <span className="font-semibold">Subject:</span> {applicationEmail.subject}
          </p>
          <p className="mt-2 whitespace-pre-wrap text-zinc-300">{applicationEmail.body}</p>
          <p className="mt-2 text-sm text-zinc-400">Attach your CV before sending.</p>
        </section>
      )}

      {interviewQuestions.length > 0 && (
        <section className="rounded-xl border border-white/10 bg-zinc-900/80 p-4">
          <h2 className="text-xl font-semibold">Interview Questions and Suggested Answers</h2>
          <div className="mt-3 space-y-3">
            {interviewQuestions.map((item, idx) => (
              <div key={`${item.kind}-${idx}`} className="rounded-md border border-white/10 bg-zinc-950 p-3">
                <p className="text-xs uppercase tracking-wider text-zinc-400">{item.kind}</p>
                <p className="mt-1 font-medium text-zinc-100">{item.question}</p>
                <p className="mt-2 text-zinc-300">{item.ideal_answer}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {careerSuggestions && (
        <section className="rounded-xl border border-white/10 bg-zinc-900/80 p-4">
          <h2 className="text-xl font-semibold">AI Career Improvement Suggestions</h2>
          <p className="mt-2 text-zinc-300">Confidence: {Math.round(careerSuggestions.confidence * 100)}%</p>
          <p className="mt-2 font-medium text-zinc-200">Suggestions</p>
          <ul className="mt-1 space-y-1 text-zinc-300">
            {careerSuggestions.suggestions.map((item, idx) => (
              <li key={`s-${idx}`}>- {item}</li>
            ))}
          </ul>
          <p className="mt-3 font-medium text-zinc-200">Upskill Plan</p>
          <ul className="mt-1 space-y-1 text-zinc-300">
            {careerSuggestions.upskill_plan.map((item, idx) => (
              <li key={`u-${idx}`}>- {item}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="rounded-xl border border-white/10 bg-zinc-900/80 p-4">
        <h2 className="text-xl font-semibold">Application Tracker</h2>
        <div className="mt-3 grid gap-2 md:grid-cols-3">
          <input
            className="rounded-md border border-zinc-700 bg-zinc-950 p-2"
            placeholder="Company"
            value={trackerCompany}
            onChange={(e) => setTrackerCompany(e.target.value)}
          />
          <input
            className="rounded-md border border-zinc-700 bg-zinc-950 p-2"
            placeholder="Role"
            value={trackerRole}
            onChange={(e) => setTrackerRole(e.target.value)}
          />
          <button className="rounded-md bg-indigo-600 px-4 py-2 hover:bg-indigo-500 disabled:opacity-60" disabled={busy} onClick={createApplication}>
            Add Application
          </button>
        </div>
        <div className="mt-4 space-y-2">
          {applications.map((app) => (
            <div key={app.id} className="rounded-md border border-white/10 bg-zinc-950 p-3">
              <p className="font-medium">
                {app.company} - {app.role}
              </p>
              <p className="text-sm text-zinc-400">
                {app.status} | Applied: {app.date_applied}
              </p>
            </div>
          ))}
          {applications.length === 0 && <p className="text-zinc-400">No applications yet.</p>}
        </div>
      </section>
    </main>
  );
}

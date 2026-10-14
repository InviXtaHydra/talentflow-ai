// Types mirroring the backend's response schemas (backend/app/schemas).

export type Role = "candidate" | "employer" | "admin";
export type RemotePolicy = "onsite" | "hybrid" | "remote";
export type RemotePreference = RemotePolicy | "any";
export type EmploymentType = "full_time" | "part_time" | "contract" | "freelance" | "internship" | "temporary";
export type ExperienceLevel = "junior" | "medior" | "senior" | "lead";
export type EducationLevel = "none" | "secondary" | "professional_bachelor" | "bachelor" | "master" | "phd";
export type SalaryPeriod = "year" | "month" | "hour";
export type JobStatus = "draft" | "published" | "closed";
export type ApplicationStatus = "saved" | "ready_to_apply" | "applied" | "in_review" | "interview" | "offer" | "rejected" | "withdrawn";
export type ExtractionStatus = "pending" | "processing" | "completed" | "needs_ocr" | "failed";
export type CvTemplate = "modern" | "minimal" | "technical";
export type CvLanguage = "nl" | "fr" | "en";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface CompanyRef {
  id: string;
  name: string;
  slug: string;
  role: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  locale: string;
  email_verified: boolean;
  onboarding_completed: boolean;
  ai_processing_consent: boolean;
  is_demo: boolean;
  companies: CompanyRef[];
  created_at: string;
}

export interface PublicConfig {
  app_name: string;
  ai_configured: boolean;
  ai_provider: string | null;
  ai_is_local: boolean;
  max_upload_mb: number;
  environment: string;
}

// ── profile ──────────────────────────────────────────────────────────────────

export interface Experience {
  id?: string;
  title: string;
  employer: string;
  location?: string | null;
  start?: string | null;
  end?: string | null;
  is_current: boolean;
  is_internship?: boolean;
  description?: string | null;
  bullets: string[];
}

export interface Education {
  id?: string;
  degree: string;
  institution: string;
  field?: string | null;
  level?: EducationLevel | null;
  start?: string | null;
  end?: string | null;
  description?: string | null;
}

export interface Certification {
  id?: string;
  name: string;
  issuer?: string | null;
  year?: number | null;
}

export interface LanguageSkill {
  code: string;
  level: "native" | "fluent" | "professional" | "basic";
}

export interface Project {
  id?: string;
  name: string;
  description?: string | null;
  url?: string | null;
  technologies: string[];
}

export interface ProfileContent {
  experiences: Experience[];
  education: Education[];
  skills: string[];
  certifications: Certification[];
  languages: LanguageSkill[];
  projects: Project[];
}

export interface ContactDetails {
  full_name?: string | null;
  email?: string | null;
  phone?: string | null;
  city?: string | null;
  linkedin_url?: string | null;
  website_url?: string | null;
}

export interface CandidateProfile {
  id: string;
  full_name: string;
  email: string;
  headline: string | null;
  summary: string | null;
  phone: string | null;
  city: string | null;
  linkedin_url: string | null;
  website_url: string | null;
  content: ProfileContent;
  onboarding_completed_at: string | null;
  confirmed_at: string | null;
  updated_at: string;
  is_demo: boolean;
}

export interface Preferences {
  desired_titles: string[];
  preferred_locations: string[];
  max_commute_km: number | null;
  remote_preference: RemotePreference;
  employment_types: EmploymentType[];
  salary_min: number | null;
  salary_currency: string;
  salary_period: SalaryPeriod;
  industries: string[];
  languages: string[];
  available_from: string | null;
  availability_note: string | null;
  updated_at?: string;
}

// ── jobs ─────────────────────────────────────────────────────────────────────

export interface CompanyBrief {
  id: string;
  name: string;
  slug: string;
  city: string | null;
  industry: string | null;
  logo_url: string | null;
  is_demo: boolean;
}

export interface Company extends CompanyBrief {
  description: string | null;
  website_url: string | null;
  size: string | null;
  open_jobs: number;
  created_at: string;
  viewer_role: string | null;
}

export interface MatchBrief {
  score: number | null;
  status: string;
  matching_skills: string[];
  missing_required_skills: string[];
  strongest_factors: string[];
  eligibility: "met" | "not_met" | "unknown";
}

export interface JobSummary {
  id: string;
  title: string;
  company: CompanyBrief;
  city: string | null;
  remote_policy: RemotePolicy;
  employment_type: EmploymentType;
  experience_level: ExperienceLevel | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string;
  salary_period: SalaryPeriod | null;
  industry: string | null;
  language: string;
  status: JobStatus;
  published_at: string | null;
  application_deadline: string | null;
  is_demo: boolean;
  skills: { name: string; is_required: boolean }[];
  saved: boolean;
  match: MatchBrief | null;
}

export interface JobDetail extends JobSummary {
  description: string;
  responsibilities: string[];
  qualifications: string[];
  benefits: string[];
  about_team: string | null;
  hiring_process: string[];
  department: string | null;
  hours_per_week: number | null;
  contract_duration_months: number | null;
  start_date: string | null;
  openings: number;
  company_profile: { description: string | null; website_url: string | null; size: string | null; open_jobs: number };
  recruiter: { full_name: string } | null;
  applicant_count: number;
  view_count: number;
  min_years_experience: number | null;
  education_level: EducationLevel | null;
  required_languages: string[];
  application_url: string | null;
  source: string;
  created_at: string;
  updated_at: string;
  application: { id: string; status: ApplicationStatus; channel: string } | null;
  can_edit: boolean;
}

export interface MatchComponent {
  key: "skills" | "experience" | "role" | "qualifications" | "preferences";
  weight: number;
  effective_weight: number;
  applicable: boolean;
  score: number | null;
  details: Record<string, unknown>;
}

export interface PreferenceCheck {
  key: "location" | "remote" | "employment_type" | "salary" | "industry";
  status: "match" | "partial" | "mismatch" | "unknown";
  [extra: string]: unknown;
}

export interface MatchResult {
  score: number | null;
  status: "ok" | "insufficient_data";
  components: MatchComponent[];
  eligibility: { status: "met" | "not_met" | "unknown"; issues: Record<string, unknown>[]; unknown: Record<string, unknown>[] };
  capped: boolean;
  matching_skills: { name: string; evidence: "listed" | "experience"; required: "yes" | "no" }[];
  missing_required_skills: { name: string }[];
  missing_preferred_skills: { name: string }[];
  relevant_experience: { id: string; title: string; employer: string; months: number | null }[];
  preference_checks: PreferenceCheck[];
  strongest_factors: string[];
  needs_review: string[];
  semantic_method: "embedding" | "lexical" | null;
  algorithm_version: string;
}

export interface MatchOut {
  job_id: string;
  score: number | null;
  status: string;
  result: MatchResult;
  algorithm_version: string;
  calculated_at: string;
  weights: Record<string, number>;
}

export interface Facets {
  industries: string[];
  cities: string[];
  skills: string[];
}

// ── CVs ──────────────────────────────────────────────────────────────────────

export interface CvDocument {
  id: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  language: string | null;
  extraction_status: ExtractionStatus;
  extraction_method: string | null;
  extraction_error: string | null;
  confirmed_at: string | null;
  created_at: string;
  is_demo: boolean;
}

export interface ExtractedCv {
  language: string | null;
  contact: ContactDetails;
  headline: string | null;
  summary: string | null;
  profile: ProfileContent;
}

export interface CvDocumentDetail extends CvDocument {
  extracted: ExtractedCv | null;
  task_id: string | null;
}

export interface CvBullet {
  text: string;
  source_refs: string[];
}

export interface CvExperience {
  source_id?: string | null;
  title: string;
  employer: string;
  location?: string | null;
  start?: string | null;
  end?: string | null;
  is_current: boolean;
  bullets: CvBullet[];
}

export interface CvContent {
  contact: ContactDetails;
  headline: string | null;
  summary: string | null;
  experiences: CvExperience[];
  education: (Education & { source_id?: string | null })[];
  skills: string[];
  certifications: (Certification & { source_id?: string | null })[];
  languages: LanguageSkill[];
  projects: (Project & { source_id?: string | null })[];
}

export interface ReviewItem {
  kind: "bullet" | "skill" | "summary" | "gap";
  section: string;
  text: string;
  reason: string;
  source_id: string | null;
}

export interface OptimizationReport {
  changes: { section: string; description: string }[];
  emphasized_keywords: string[];
  questions: { question: string; reason: string | null }[];
  review_items: ReviewItem[];
  gap: {
    matching_skills: string[];
    missing_required_skills: string[];
    missing_preferred_skills: string[];
    keywords_missing_from_cv: string[];
    relevant_experience_ids: string[];
  };
  target_language: string;
}

export interface CvVersionSummary {
  id: string;
  kind: "original" | "optimized" | "manual";
  status: "generating" | "ready" | "failed";
  title: string;
  language: CvLanguage;
  template: CvTemplate;
  source_cv_id: string | null;
  target_job_id: string | null;
  target_job_title: string | null;
  target_company_name: string | null;
  score_before: number | null;
  score_after: number | null;
  is_simulated: boolean;
  created_at: string;
  updated_at: string;
  user_edited_at: string | null;
  last_exported_at: string | null;
}

export interface CvVersionDetail extends CvVersionSummary {
  content: CvContent | null;
  generated_content: CvContent | null;
  original_content: CvContent | null;
  optimization: OptimizationReport | null;
  match_before: MatchResult | null;
  match_after: MatchResult | null;
  provider: string | null;
  model: string | null;
  error_message: string | null;
  task_id: string | null;
  task_status: string | null;
  task_progress: number | null;
  task_message: string | null;
}

export interface AnalysisCheck {
  key: string;
  passed: boolean;
  weight: number;
  detail: Record<string, unknown>;
}

export interface CvAnalysis {
  id: string;
  cv_document_id: string | null;
  status: string;
  method: string;
  quality_score: number | null;
  checks: AnalysisCheck[];
  strengths: string[];
  suggestions: string[];
  provider: string | null;
  model: string | null;
  created_at: string;
}

export interface TaskStatus {
  id: string;
  type: string;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  progress: number;
  progress_message: string | null;
  error_code: string | null;
  error_message: string | null;
  result: Record<string, unknown> | null;
  created_at: string;
  finished_at: string | null;
}

// ── applications ─────────────────────────────────────────────────────────────

export interface StatusHistory {
  from_status: ApplicationStatus | null;
  to_status: ApplicationStatus;
  changed_by_role: string | null;
  note: string | null;
  created_at: string;
}

export interface Application {
  id: string;
  job: JobSummary;
  status: ApplicationStatus;
  channel: "platform" | "external";
  cv_version_id: string | null;
  cv_version_title: string | null;
  notes: string | null;
  cover_letter: string | null;
  applied_at: string | null;
  created_at: string;
  updated_at: string;
  history: StatusHistory[];
}

export interface Applicant {
  id: string;
  job_id: string;
  job_title: string;
  company_id: string;
  candidate_name: string;
  candidate_email: string;
  candidate_city: string | null;
  candidate_headline: string | null;
  status: ApplicationStatus;
  applied_at: string | null;
  cover_letter: string | null;
  has_cv: boolean;
  matching_skills: string[];
  missing_required_skills: string[];
  history: StatusHistory[];
  cv: CvContent | null;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string | null;
  link: string | null;
  read_at: string | null;
  created_at: string;
}

export interface AssistantMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  job_ids: string[];
  created_at: string;
}

export interface Member {
  user_id: string;
  full_name: string;
  email: string;
  role: string;
}

export interface Session {
  id: string;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  user_agent: string | null;
  current: boolean;
}

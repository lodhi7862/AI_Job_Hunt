CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  full_name VARCHAR(255) NOT NULL,
  hashed_password VARCHAR(255) NOT NULL,
  role VARCHAR(50) DEFAULT 'user',
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resumes (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  original_filename VARCHAR(255),
  raw_text TEXT NOT NULL,
  structured_data JSONB DEFAULT '{}'::jsonb,
  ats_issues JSONB DEFAULT '[]'::jsonb,
  embedding vector(1536),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  title VARCHAR(255) NOT NULL,
  company VARCHAR(255) DEFAULT '',
  description TEXT NOT NULL,
  analysis JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_matches (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  resume_id INT REFERENCES resumes(id),
  job_id INT REFERENCES jobs(id),
  score FLOAT NOT NULL,
  missing_skills JSONB DEFAULT '[]'::jsonb,
  reasoning TEXT NOT NULL,
  strengths JSONB DEFAULT '[]'::jsonb,
  weaknesses JSONB DEFAULT '[]'::jsonb,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cover_letters (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(id),
  job_id INT NOT NULL REFERENCES jobs(id),
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interview_questions (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(id),
  job_id INT NOT NULL REFERENCES jobs(id),
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  kind VARCHAR(50) DEFAULT 'behavioral'
);

CREATE TABLE IF NOT EXISTS applications (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(id),
  company VARCHAR(255) NOT NULL,
  role VARCHAR(255) NOT NULL,
  date_applied VARCHAR(30) NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'Applied',
  notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS linkedin_profiles (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(id),
  profile_url VARCHAR(500) NOT NULL DEFAULT '',
  profile_text TEXT NOT NULL DEFAULT '',
  analysis JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS ai_logs (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(id),
  provider VARCHAR(50) NOT NULL,
  prompt TEXT NOT NULL,
  response TEXT NOT NULL,
  confidence FLOAT NOT NULL DEFAULT 0.8,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_user_id ON job_matches(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_user_id ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_linkedin_profiles_user_id ON linkedin_profiles(user_id);

-- Production Database Schema for Quiz Platform
-- Exact implementation as specified in assignment

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Chapters table: stores PDF metadata and Gemini references
CREATE TABLE IF NOT EXISTS chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gemini_file_id VARCHAR UNIQUE NOT NULL,
    subject VARCHAR(50),
    class_level INTEGER,
    title VARCHAR(255),
    topics JSONB,  -- ["quadratic_formula", "discriminant"]
    status VARCHAR(20) DEFAULT 'indexed',
    created_at TIMESTAMP DEFAULT NOW()
);

-- User progress table: tracks chapter completion
CREATE TABLE IF NOT EXISTS user_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    chapter_id UUID REFERENCES chapters(id) ON DELETE CASCADE,
    time_spent INTEGER,
    scroll_progress DECIMAL(4,2),
    is_completed BOOLEAN DEFAULT FALSE,
    completion_method TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);


-- Quizzes table: stores generated quiz questions
CREATE TABLE IF NOT EXISTS quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID REFERENCES chapters(id) ON DELETE CASCADE,
    difficulty VARCHAR(20),
    questions JSONB NOT NULL,
    variant_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Quiz attempts table: stores submissions and grading
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    quiz_id UUID REFERENCES quizzes(id) ON DELETE CASCADE,
    answers JSONB,
    scores JSONB,
    total_score DECIMAL(4,2),
    weak_topics JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Performance Table Indexes 
CREATE INDEX IF NOT EXISTS idx_user_progress_user ON user_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_chapter ON user_progress(chapter_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user ON quiz_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_quiz ON quiz_attempts(quiz_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_variant ON quizzes(variant_hash);
CREATE INDEX IF NOT EXISTS idx_chapters_gemini_file ON chapters(gemini_file_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for user_progress
CREATE TRIGGER update_user_progress_updated_at 
    BEFORE UPDATE ON user_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
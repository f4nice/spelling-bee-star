CREATE DATABASE IF NOT EXISTS booklearner
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE booklearner;

CREATE TABLE IF NOT EXISTS analyses (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  query_text VARCHAR(255) NOT NULL,
  status VARCHAR(40) NOT NULL,
  title VARCHAR(512) NULL,
  authors_text VARCHAR(1024) NULL,
  source_name VARCHAR(160) NULL,
  source_url VARCHAR(1024) NULL,
  notice TEXT NULL,
  stats_json JSON NULL,
  result_json JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_analyses_created_at (created_at),
  KEY idx_analyses_query_text (query_text)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS analysis_quotes (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  analysis_id BIGINT UNSIGNED NOT NULL,
  position INT NOT NULL,
  quote_text TEXT NOT NULL,
  note TEXT NULL,
  score DECIMAL(8, 2) NULL,
  PRIMARY KEY (id),
  KEY idx_quotes_analysis_id (analysis_id),
  CONSTRAINT fk_quotes_analysis
    FOREIGN KEY (analysis_id) REFERENCES analyses(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS analysis_vocabulary (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  analysis_id BIGINT UNSIGNED NOT NULL,
  position INT NOT NULL,
  word VARCHAR(120) NOT NULL,
  part_of_speech VARCHAR(80) NULL,
  definition_text TEXT NULL,
  example_text TEXT NULL,
  memory_hint TEXT NULL,
  occurrence_count INT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  KEY idx_vocabulary_analysis_id (analysis_id),
  KEY idx_vocabulary_word (word),
  CONSTRAINT fk_vocabulary_analysis
    FOREIGN KEY (analysis_id) REFERENCES analyses(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS booklearner_clicked_words (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  analysis_id BIGINT UNSIGNED NULL,
  book_title VARCHAR(512) NULL,
  word VARCHAR(120) NOT NULL,
  part_of_speech VARCHAR(80) NULL,
  definition_text TEXT NULL,
  example_text TEXT NULL,
  memory_hint TEXT NULL,
  occurrence_count INT NOT NULL DEFAULT 0,
  click_count INT NOT NULL DEFAULT 1,
  first_clicked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_clicked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_clicked_analysis_word (analysis_id, word),
  KEY idx_clicked_word (word),
  KEY idx_clicked_last_clicked_at (last_clicked_at),
  CONSTRAINT fk_clicked_analysis
    FOREIGN KEY (analysis_id) REFERENCES analyses(id)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

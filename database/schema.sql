CREATE DATABASE IF NOT EXISTS job_applications
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE job_applications;

CREATE TABLE IF NOT EXISTS applications (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    photo_key VARCHAR(500) NOT NULL,
    cv_key VARCHAR(500) NOT NULL,
    video_key VARCHAR(500) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;

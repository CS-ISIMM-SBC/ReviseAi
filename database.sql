-- Création de la base de données
CREATE DATABASE IF NOT EXISTS aiquizdb;
USE aiquizdb;

-- Table pour stocker les sessions de quiz
CREATE TABLE IF NOT EXISTS quiz_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    topic VARCHAR(255) NOT NULL,       -- Le sujet ou nom du fichier
    difficulty VARCHAR(50) NOT NULL,   -- Facile, Moyen, Difficile
    summary TEXT NOT NULL,             -- Le résumé généré par l'IA
    score INT DEFAULT 0,               -- Le score obtenu par l'étudiant
    total_questions INT DEFAULT 10,    -- Nombre total de questions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
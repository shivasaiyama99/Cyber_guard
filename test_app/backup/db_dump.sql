-- VulnLab Database Backup (CONFIDENTIAL)
-- Generated: 2026-03-14
-- This file should NOT be accessible from the web!

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    password TEXT,  -- PLAINTEXT PASSWORDS!
    email TEXT,
    role TEXT,
    credit_card TEXT,
    ssn TEXT
);

INSERT INTO users VALUES(1,'admin','admin123','admin@vulnlab.local','admin','4111-1111-1111-1111','123-45-6789');
INSERT INTO users VALUES(2,'john','password','john@vulnlab.local','user','4222-2222-2222-2222','234-56-7890');
INSERT INTO users VALUES(3,'jane','letmein','jane@vulnlab.local','user','4333-3333-3333-3333','345-67-8901');

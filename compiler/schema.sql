CREATE TABLE Projects (
    repo_name VARCHAR(50) PRIMARY KEY,
    readme_update_time DATETIME NOT NULL,
    description_generated INTEGER NOT NULL DEFAULT 0,
    description TEXT NOT NULL DEFAULT ""
);

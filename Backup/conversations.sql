CREATE TABLE conversations (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NULL,
    is_group BIT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE()
);
INSERT INTO conversations (name, is_group) VALUES ('Nhóm học tập', 1);

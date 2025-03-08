CREATE TABLE users_accounts (
    id INT IDENTITY(1,1) PRIMARY KEY,
    username NVARCHAR(50) UNIQUE NOT NULL,
    email NVARCHAR(100) UNIQUE NOT NULL,
    password_hash NVARCHAR(255) NOT NULL,
    full_name NVARCHAR(100) NULL,
    avatar_url NVARCHAR(255) NULL,
    created_at DATETIME DEFAULT GETDATE()
);

INSERT INTO users (username, email, password_hash, full_name)  
VALUES (N'user1', N'user1@example.com', N'hashed_password', N'Nguyễn Văn A',NULL);
SELECT * FROM users;


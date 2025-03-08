CREATE TABLE messages (
    id INT IDENTITY(1,1) PRIMARY KEY,
    conversation_id INT NOT NULL,
    sender_id INT NOT NULL,
    content NVARCHAR(MAX) NULL,
    file_url NVARCHAR(255) NULL,
    file_type NVARCHAR(50) NULL,
    sent_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (sender_id) REFERENCES users(id)
);

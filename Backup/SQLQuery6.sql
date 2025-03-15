-- Kiểm tra bảng đã tồn tại chưa
SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'conversations';

-- Kiểm tra danh sách cột của bảng
SELECT COLUMN_NAME, DATA_TYPE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'conversations';

-- Kiểm tra khóa ngoại có tạo đúng không
SELECT 
    OBJECT_NAME(fk.parent_object_id) AS TableName, 
    COL_NAME(fc.parent_object_id, fc.parent_column_id) AS ColumnName,
    OBJECT_NAME(fk.referenced_object_id) AS ReferencedTableName, 
    COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS ReferencedColumnName
FROM sys.foreign_keys AS fk
JOIN sys.foreign_key_columns AS fc 
ON fk.object_id = fc.constraint_object_id
WHERE OBJECT_NAME(fk.referenced_object_id) = 'conversations';

-- Kiểm tra dữ liệu trong bảng conversations
SELECT * FROM conversations;

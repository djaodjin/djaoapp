PRAGMA writable_schema = 1;
UPDATE SQLITE_MASTER SET SQL = replace(SQL, '"email" varchar(254) NOT NULL', '"email" varchar(254)') WHERE NAME = 'auth_user';
PRAGMA writable_schema = 0;

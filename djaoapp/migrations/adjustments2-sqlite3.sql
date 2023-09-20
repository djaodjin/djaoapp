CREATE UNIQUE INDEX uniq_email ON auth_user(email) WHERE email IS NOT NULL;

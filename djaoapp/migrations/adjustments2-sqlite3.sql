CREATE UNIQUE INDEX uniq_email ON auth_user(email) WHERE email IS NOT NULL;
UPDATE rules_app set show_edit_tools=1;

-- CREATE USER FOR OPERATOR
CREATE USER 'operator_user'@'localhost' IDENTIFIED BY 'op123';
GRANT SELECT, INSERT, UPDATE ON dbms.* TO 'operator_user'@'localhost';

-- CREATE USER FOR MANAGER
CREATE USER 'manager_user'@'localhost' IDENTIFIED BY 'manager123';
GRANT ALL PRIVILEGES ON dbms.* TO 'manager_user'@'localhost';

-- REVOKE PRIVILEGES EXAMPLE
REVOKE UPDATE ON dbms.* FROM 'operator_user'@'localhost';

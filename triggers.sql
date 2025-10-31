DELIMITER //

CREATE TRIGGER before_booking_insert
BEFORE INSERT ON BOOKINGS
FOR EACH ROW
BEGIN
    IF NEW.price IS NULL OR NEW.price <= 0 THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Booking price must be greater than zero';
    END IF;
END //

CREATE TRIGGER before_booking_update
BEFORE UPDATE ON BOOKINGS
FOR EACH ROW
BEGIN
    IF NEW.price IS NULL OR NEW.price <= 0 THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Booking price must be greater than zero';
    END IF;
END //

DELIMITER //
CREATE TRIGGER after_booking_delete
AFTER DELETE ON BOOKINGS
FOR EACH ROW
BEGIN
    DELETE FROM REVENUE WHERE booking_id = OLD.booking_id;
END //
DELIMITER ;

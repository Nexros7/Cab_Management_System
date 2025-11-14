DELIMITER //


CREATE TRIGGER check_booking_price
BEFORE INSERT ON BOOKINGS
FOR EACH ROW
BEGIN
    IF NEW.price <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Price cannot be zero or negative';
    END IF;
END //


CREATE TRIGGER auto_insert_payment
AFTER INSERT ON BOOKINGS
FOR EACH ROW
BEGIN
    IF NEW.payment_type = 'CARD' THEN
        INSERT INTO PAYMENTS(booking_id,card_number,CVV,expiry,price)
        SELECT NEW.booking_id, c.card_number, c.CVV, c.expiry, NEW.price
        FROM CLIENTS c
        WHERE c.client_id = NEW.client_id;
    END IF;
END //

CREATE TRIGGER log_deleted_booking
AFTER DELETE ON BOOKINGS
FOR EACH ROW
BEGIN
    DELETE FROM REVENUE
    WHERE booking_id = OLD.booking_id;
END //

CREATE TRIGGER add_revenue_entry
AFTER INSERT ON BOOKINGS
FOR EACH ROW
BEGIN
    INSERT INTO REVENUE(booking_id,d_id,revenue)
    VALUES(NEW.booking_id,NEW.d_id,NEW.price);
END //

DELIMITER ;

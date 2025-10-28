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


CREATE TRIGGER update_car_status
AFTER UPDATE ON CARS
FOR EACH ROW
BEGIN
    IF NEW.d_id IS NOT NULL THEN
        UPDATE CARS SET status = 'In service' WHERE registration = NEW.registration;
    END IF;
END //


CREATE TABLE IF NOT EXISTS BOOKINGS_LOG(
    booking_id INT,
    d_id INT,
    client_id INT,
    deleted_at DATETIME
);

CREATE TRIGGER log_deleted_booking
AFTER DELETE ON BOOKINGS
FOR EACH ROW
BEGIN
    INSERT INTO BOOKINGS_LOG(booking_id,d_id,client_id,deleted_at)
    VALUES(OLD.booking_id,OLD.d_id,OLD.client_id,NOW());
END //


CREATE TRIGGER add_revenue_entry
AFTER INSERT ON BOOKINGS
FOR EACH ROW
BEGIN
    INSERT INTO REVENUE(booking_id,d_id,revenue)
    VALUES(NEW.booking_id,NEW.d_id,NEW.price);
END //

DELIMITER ;

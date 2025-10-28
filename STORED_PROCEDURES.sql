DELIMITER //

CREATE PROCEDURE GetDriverBookings(IN driverID INT)
BEGIN
    SELECT b.booking_id, c.first_name AS client_name, b.pickup_location, b.destination, b.price, b.payment_type
    FROM BOOKINGS b
    JOIN CLIENTS c ON b.client_id = c.client_id
    WHERE b.d_id = driverID;
END //


CREATE PROCEDURE GetDriverRevenue(IN driverID INT)
BEGIN
    SELECT d.first_name, d.last_name, SUM(r.revenue) AS total_revenue
    FROM REVENUE r
    JOIN DRIVERS d ON d.d_id = r.d_id
    WHERE r.d_id = driverID
    GROUP BY r.d_id;
END //


CREATE PROCEDURE AddBooking(
    IN op INT,
    IN drv INT,
    IN cli INT,
    IN book_type VARCHAR(10),
    IN book_time DATETIME,
    IN pickup DATETIME,
    IN pickup_loc VARCHAR(30),
    IN dest VARCHAR(30),
    IN pay_type VARCHAR(5),
    IN price INT
)
BEGIN
    IF price <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Price must be positive';
    ELSE
        INSERT INTO BOOKINGS(op_id,d_id,client_id,type_booking,time_of_booking,time_of_pickup,pickup_location,destination,payment_type,price)
        VALUES(op,drv,cli,book_type,book_time,pickup,pickup_loc,dest,pay_type,price);
    END IF;
END //


CREATE PROCEDURE GetDriverShift(IN driverID INT)
BEGIN
    SELECT d.first_name, d.last_name, s.shift_start_time, s.shift_hours
    FROM DRIVERS d
    JOIN D_SHIFTS s ON d.d_id = s.d_id
    WHERE d.d_id = driverID;
END //

-
CREATE PROCEDURE GetAvailableCars()
BEGIN
    SELECT registration, car_make, car_model, status
    FROM CARS
    WHERE status = 'Available';
END //

DELIMITER ;

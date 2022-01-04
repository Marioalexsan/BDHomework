-- mysql
-- Initialize MySQL database for an electronics shop


-- Employee table
CREATE TABLE employee (
  employee_id INT PRIMARY KEY,
  first_name VARCHAR(50) NOT NULL,
  last_name VARCHAR(50) NOT NULL,
  manager_id INT,  -- Allow null

  CONSTRAINT employee_manager_id_fk
  FOREIGN KEY (manager_id) REFERENCES employee(employee_id),

  -- Names must be made of letters, space and hyphens
  CONSTRAINT employee_name_chk
  CHECK (NOT REGEXP_LIKE(first_name, '[^a-zA-Z\ \-]+') AND NOT REGEXP_LIKE(last_name, '[^a-zA-Z\ \-]+'))
);

INSERT INTO employee VALUES(100, 'Joseph', 'Joestar', NULL); -- mega manager
INSERT INTO employee VALUES(101, 'John', 'Smith', 100);
INSERT INTO employee VALUES(102, 'Mary', 'Snow', 100);

INSERT INTO employee VALUES(103, 'Alex', 'Woodrow', 100); -- manager
INSERT INTO employee VALUES(104, 'Amy', 'Wilson', 103);
INSERT INTO employee VALUES(105, 'Helen', 'Washington', 103);
INSERT INTO employee VALUES(106, 'Mark', 'Hunter', 103);

INSERT INTO employee VALUES(107, 'Teddy', 'Stone', 100); -- manager
INSERT INTO employee VALUES(108, 'Adam', 'Ruby', 107);
INSERT INTO employee VALUES(109, 'Arthur', 'Capek', 107);
INSERT INTO employee VALUES(110, 'Susan', 'Dawn', 107);

-- Employee extra info - 1:1 relationship with employee table
CREATE TABLE employee_extended_info (
  employee_id INT PRIMARY KEY,
  hire_date DATE,
  is_intern BOOLEAN NOT NULL,
  
  CONSTRAINT employee_extended_info_employee_id_fk 
  FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE CASCADE
);

INSERT INTO employee_extended_info VALUES(106, NULL, TRUE);

-- Products that are sold by this shop
CREATE TABLE product_type (
  product_type_id INT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description VARCHAR(4096) DEFAULT(NULL) -- Allow null
);

INSERT INTO product_type VALUES(100, 'AlienWare PowerPC 9000', 'Personal Computer');
INSERT INTO product_type VALUES(101, 'AlienWare PowerPC 9500', 'Personal Computer');
INSERT INTO product_type VALUES(102, 'AMD Radeon R7 240', 'Graphics Card');
INSERT INTO product_type VALUES(103, 'NVIDIA RTX 3080', 'Graphics Card');
INSERT INTO product_type VALUES(104, 'SONY PlayStation 5', 'Game Console');
INSERT INTO product_type VALUES(105, 'ZTE F660', 'Internet Modem with Optic Fiber');
INSERT INTO product_type VALUES(106, 'LENOVO Ideapad 330S', 'Laptop');
INSERT INTO product_type VALUES(107, 'APPLE iPhone 8', 'Smartphone');
INSERT INTO product_type VALUES(108, 'Power Extender 5 ports', 'Generic Appliance');
INSERT INTO product_type VALUES(109, 'HIPOWER Power Bank 25600mAh', 'Generic Appliance');

-- Table of purchases that were done at this shop
CREATE TABLE purchase (
  purchase_id INT PRIMARY KEY,
  seller_id INT,  -- Allow null
  
  CONSTRAINT purchase_seller_id_fk
  FOREIGN KEY (seller_id) REFERENCES employee(employee_id)
);

INSERT INTO purchase VALUES(13079, 104);
INSERT INTO purchase VALUES(13080, 105);
INSERT INTO purchase VALUES(13081, 106);
INSERT INTO purchase VALUES(13082, 106);

-- A specific product that was sold in a purchase. There can be many products sold in a purchase
CREATE TABLE product_purchase (
  product_id INT PRIMARY KEY,
  product_type_id INT NOT NULL,
  purchase_id INT NOT NULL,
  
  CONSTRAINT product_purchase_product_type_id_fk
  FOREIGN KEY (product_type_id) REFERENCES product_type(product_type_id),
  
  CONSTRAINT product_purchase_purchase_id_fk
  FOREIGN KEY (purchase_id) REFERENCES purchase(purchase_id)
);

INSERT INTO product_purchase VALUES(20000, 100, 13079);
INSERT INTO product_purchase VALUES(20001, 105, 13079);
INSERT INTO product_purchase VALUES(20002, 108, 13079);

INSERT INTO product_purchase VALUES(20003, 106, 13080);
INSERT INTO product_purchase VALUES(20004, 101, 13080);
INSERT INTO product_purchase VALUES(20005, 108, 13080);

INSERT INTO product_purchase VALUES(20006, 107, 13081);

INSERT INTO product_purchase VALUES(20007, 107, 13082);
INSERT INTO product_purchase VALUES(20008, 108, 13082);

-- Available payment methods
CREATE TABLE payment_method (
  payment_method_id INT PRIMARY KEY,
  name VARCHAR(100) NOT NULL
);

INSERT INTO payment_method VALUES(0, 'Credit Card');
INSERT INTO payment_method VALUES(1, 'Cash');
INSERT INTO payment_method VALUES(2, 'Sale Offer / Bonus');

-- A source of money used to pay a purchase. Multiple payment options can be used in a single purchase (say, you pay with both card and cash)
CREATE TABLE payment (
  payment_id INT PRIMARY KEY,
  purchase_id INT NOT NULL,
  payment_method_id INT NOT NULL,
  amount DECIMAL(10, 2) NOT NULL,
  
  CONSTRAINT payment_purchase_id_fk
  FOREIGN KEY (purchase_id) REFERENCES purchase(purchase_id),
  
  CONSTRAINT payment_payment_method_id_fk
  FOREIGN KEY (payment_method_id) REFERENCES payment_method(payment_method_id)
);

INSERT INTO payment VALUES (23765, 13079, 0, 500.00);
INSERT INTO payment VALUES (23766, 13079, 1, 12.55);
INSERT INTO payment VALUES (23767, 13080, 0, 500.00);
INSERT INTO payment VALUES (23768, 13081, 1, 500.00);
INSERT INTO payment VALUES (23769, 13082, 0, 500.00);
INSERT INTO payment VALUES (23770, 13082, 1, 12.55);
INSERT INTO payment VALUES (23771, 13082, 2, 120.00);

-- Shop task / commisions / etc (let's say this shop also acts as a repair shop)
CREATE TABLE task (
	task_id INT PRIMARY KEY,
	description VARCHAR(500) NOT NULL,
	complete BOOLEAN DEFAULT(FALSE) NOT NULL
);

INSERT INTO task (task_id, description) VALUES(100, 'Repair order Corsair UltraPC 9500 submitted by client Miron Alexandru');
INSERT INTO task (task_id, description) VALUES(101, 'Repair order Corsair UltraPC 9000 submitted by client John Johnson');
INSERT INTO task (task_id, description) VALUES(102, 'Maintain shop infrastructure');

CREATE TABLE task_assignment (
  task_id INT NOT NULL,
  employee_id INT NOT NULL,
  
  CONSTRAINT task_assignment_unique
  UNIQUE(task_id, employee_id),
	
  CONSTRAINT task_assignment_task_id_fk
  FOREIGN KEY (task_id) REFERENCES task(task_id),
  
  CONSTRAINT task_assignment_employee_id_fk
  FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
);

INSERT INTO task_assignment VALUES(100, 108);
INSERT INTO task_assignment VALUES(100, 109);
INSERT INTO task_assignment VALUES(101, 108);
INSERT INTO task_assignment VALUES(101, 109);
INSERT INTO task_assignment VALUES(102, 110);
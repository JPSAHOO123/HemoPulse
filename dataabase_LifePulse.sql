-- ==========================================
-- LIFEPULSE DATABASE INITIALIZATION SCRIPT
-- ==========================================

CREATE DATABASE IF NOT EXISTS lifepulse_db;
USE lifepulse_db;

-- Foreign key checks ko temporarily OFF karo taaki clean drop ho sake
SET FOREIGN_KEY_CHECKS = 0;

-- Clean Up Old Tables
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS health_metrics;
DROP TABLE IF EXISTS acceptor_requests;
DROP TABLE IF EXISTS donor_logs;
DROP TABLE IF EXISTS vault_transactions;
DROP TABLE IF EXISTS inventory_vault;
DROP TABLE IF EXISTS hospitals;
DROP TABLE IF EXISTS users;

-- Foreign key checks wapas ON
SET FOREIGN_KEY_CHECKS = 1;

-- ==========================================
-- TABLE SCHEMAS CREATION
-- ==========================================

-- 1. Users Table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    age INT,
    gender VARCHAR(20),
    blood_group VARCHAR(10) DEFAULT 'Not Set',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Health Metrics Table
CREATE TABLE health_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    blood_pressure VARCHAR(20),
    heart_rate INT,
    blood_sugar INT,
    weight FLOAT,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. Appointments Table
CREATE TABLE appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    doctor_name VARCHAR(100) NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status VARCHAR(20) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. Inventory Vault (Storage Component)
CREATE TABLE inventory_vault (
    id INT AUTO_INCREMENT PRIMARY KEY,
    blood_group VARCHAR(10) NOT NULL,
    component_type VARCHAR(50) NOT NULL, -- Whole Blood, RBC, Platelets, FFP, etc.
    units INT NOT NULL DEFAULT 1,
    donation_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    status ENUM('Available', 'Reserved', 'Expired', 'Dispatched') DEFAULT 'Available',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Donor Logs Table
CREATE TABLE donor_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    blood_group VARCHAR(10) NOT NULL,
    component_type VARCHAR(50) NOT NULL,
    units INT NOT NULL DEFAULT 1,
    donation_date DATE DEFAULT (CURRENT_DATE),
    vault_id INT,
    medical_condition VARCHAR(100) DEFAULT 'Healthy',
    status VARCHAR(20) DEFAULT 'Approved',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (vault_id) REFERENCES inventory_vault(id) ON DELETE SET NULL
);

-- 6. Acceptor Requests Table
CREATE TABLE acceptor_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    patient_name VARCHAR(100) NOT NULL,
    blood_group VARCHAR(10) NOT NULL,
    component_type VARCHAR(50) NOT NULL,
    units_needed INT NOT NULL,
    disease_reason VARCHAR(100) DEFAULT 'General Emergency',
    status ENUM('Pending', 'Fulfilled (Vault)', 'Fulfilled (Direct)', 'Cancelled') DEFAULT 'Pending',
    request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 7. Vault Transactions Ledger Table (IN/OUT Ledger)
CREATE TABLE vault_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    txn_type VARCHAR(10) NOT NULL,
    person_name VARCHAR(100) NOT NULL,
    blood_group VARCHAR(10) NOT NULL,
    component_type VARCHAR(50) NOT NULL,
    units INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Hospitals Master Table
CREATE TABLE hospitals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hospital_name VARCHAR(150) NOT NULL,
    state VARCHAR(50) NOT NULL,
    district VARCHAR(50) NOT NULL,
    contact_number VARCHAR(15),
    address TEXT
);

-- ==========================================
-- ODISHA ALL DISTRICTS HOSPITALS SEED DATA
-- ==========================================

INSERT INTO hospitals (hospital_name, state, district, contact_number, address) VALUES
-- Khordha / Bhubaneswar
('AIIMS Hospital', 'Odisha', 'Khordha', '+916742476789', 'Sijua, Patrapada, Bhubaneswar'),
('Capital Hospital', 'Odisha', 'Khordha', '+916742391983', 'Unit 6, Bhubaneswar'),
('SUM Ultimate Medicare', 'Odisha', 'Khordha', '+916742386281', 'Kalinga Nagar, Bhubaneswar'),
('KIMS Hospital & Medical College', 'Odisha', 'Khordha', '+916742725182', 'Patia, Bhubaneswar'),
('AMRI Hospital', 'Odisha', 'Khordha', '+916746666666', 'Khandagiri, Bhubaneswar'),
('Apollo Hospitals', 'Odisha', 'Khordha', '+916746661016', 'Sainik School Road, Bhubaneswar'),

-- Cuttack
('SCB Medical College & Hospital', 'Odisha', 'Cuttack', '+916712414080', 'Mangalabag, Cuttack'),
('SVP PG Institute of Paediatrics (Sishu Bhawan)', 'Odisha', 'Cuttack', '+916712304282', 'Ainthapali, Cuttack'),
('Ashwini Hospital', 'Odisha', 'Cuttack', '+916712363030', 'Sector 1, CDA, Cuttack'),
('City Hospital Cuttack', 'Odisha', 'Cuttack', '+916712301014', 'Buxibazar, Cuttack'),

-- Ganjam / Berhampur
('MKCG Medical College & Hospital', 'Odisha', 'Ganjam', '+916802292746', 'Medical College Road, Berhampur'),
('City Hospital Berhampur', 'Odisha', 'Ganjam', '+916802220102', 'Old Bus Stand, Berhampur'),
('District Headquarters Hospital (DHH) Bhanjanagar', 'Odisha', 'Ganjam', '+916821240100', 'Bhanjanagar, Ganjam'),

-- Sambalpur
('VIMSAR Medical College & Hospital', 'Odisha', 'Sambalpur', '+916632430768', 'Burla, Sambalpur'),
('District Headquarters Hospital (DHH) Sambalpur', 'Odisha', 'Sambalpur', '+916632400100', 'Kacheri Road, Sambalpur'),

-- Sundargarh / Rourkela
('Rourkela Steel Plant (RSP) IGH Hospital', 'Odisha', 'Sundargarh', '+916612510121', 'Sector 19, Rourkela'),
('Hi-Tech Medical College & Hospital', 'Odisha', 'Sundargarh', '+916612400500', 'Rourkela'),
('District Headquarters Hospital (DHH) Sundargarh', 'Odisha', 'Sundargarh', '+916622272200', 'Regent Market, Sundargarh'),

-- Balasore
('Fakir Mohan Medical College & Hospital', 'Odisha', 'Balasore', '+916782262002', 'Remuna, Balasore'),
('District Headquarters Hospital (DHH) Balasore', 'Odisha', 'Balasore', '+916782262100', 'Station Road, Balasore'),

-- Dhenkanal
('District Headquarters Hospital (DHH) Dhenkanal', 'Odisha', 'Dhenkanal', '+916762226100', 'Ganesh Bazar, Dhenkanal'),

-- Angul
('District Headquarters Hospital (DHH) Angul', 'Odisha', 'Angul', '+916764230400', 'Ambalanagar, Angul'),
('Jindal Steel & Power (JSP) Fortis Clinic', 'Odisha', 'Angul', '+916764220000', 'Nisha, Angul'),

-- Puri
('District Headquarters Hospital (DHH) Puri', 'Odisha', 'Puri', '+916752222100', 'VIP Road, Puri'),
('Shree Jagannath Medical College & Hospital', 'Odisha', 'Puri', '+916752230000', 'Samangara, Puri'),

-- Koraput
('SLN Medical College & Hospital', 'Odisha', 'Koraput', '+916852250100', 'Koraput Town, Koraput'),
('District Headquarters Hospital (DHH) Jeypore', 'Odisha', 'Koraput', '+916854232100', 'Jeypore, Koraput'),

-- Mayurbhanj / Baripada
('PRM Medical College & Hospital', 'Odisha', 'Mayurbhanj', '+916792252100', 'Baripada, Mayurbhanj'),

-- Balangir
('BB Medical College & Hospital', 'Odisha', 'Balangir', '+916652230100', 'Balangir Town, Balangir'),

-- Kalahandi / Bhawanipatna
('Government Medical College & Hospital Bhawanipatna', 'Odisha', 'Kalahandi', '+916670230100', 'Bhawanipatna, Kalahandi'),

-- Kendujhar (Keonjhar)
('Dharani Dhar Medical College & Hospital', 'Odisha', 'Kendujhar', '+916766255100', 'Keonjhar Town, Kendujhar'),

-- Jharsuguda
('District Headquarters Hospital (DHH) Jharsuguda', 'Odisha', 'Jharsuguda', '+916645272100', 'Jharsuguda Town'),

-- Jagatsinghpur
('District Headquarters Hospital (DHH) Jagatsinghpur', 'Odisha', 'Jagatsinghpur', '+916724220100', 'Jagatsinghpur'),

-- Kendrapara
('District Headquarters Hospital (DHH) Kendrapara', 'Odisha', 'Kendrapara', '+916727220100', 'Kendrapara Town'),

-- Bhadrak
('District Headquarters Hospital (DHH) Bhadrak', 'Odisha', 'Bhadrak', '+916784250100', 'Bhadrak Town'),

-- Jajpur
('District Headquarters Hospital (DHH) Jajpur', 'Odisha', 'Jajpur', '+916728222100', 'Jajpur Town'),

-- Nayagarh
('District Headquarters Hospital (DHH) Nayagarh', 'Odisha', 'Nayagarh', '+916753252100', 'Nayagarh Town'),

-- Rayagada
('District Headquarters Hospital (DHH) Rayagada', 'Odisha', 'Rayagada', '+916856222100', 'Rayagada Town'),

-- Nabarangpur
('District Headquarters Hospital (DHH) Nabarangpur', 'Odisha', 'Nabarangpur', '+916858222100', 'Nabarangpur Town'),

-- Malkangiri
('District Headquarters Hospital (DHH) Malkangiri', 'Odisha', 'Malkangiri', '+916861230100', 'Malkangiri Town'),

-- Nuapada
('District Headquarters Hospital (DHH) Nuapada', 'Odisha', 'Nuapada', '+916678223100', 'Nuapada Town'),

-- Kandhamal / Phulbani
('District Headquarters Hospital (DHH) Phulbani', 'Odisha', 'Kandhamal', '+916842253100', 'Phulbani, Kandhamal'),

-- Boudh
('District Headquarters Hospital (DHH) Boudh', 'Odisha', 'Boudh', '+916841222100', 'Boudh Town'),

-- Deogarh
('District Headquarters Hospital (DHH) Deogarh', 'Odisha', 'Deogarh', '+916641226100', 'Deogarh Town'),

-- Gajapati
('District Headquarters Hospital (DHH) Paralakhemundi', 'Odisha', 'Gajapati', '+916815222100', 'Paralakhemundi, Gajapati'),

-- Subarnapur (Sonepur)
('District Headquarters Hospital (DHH) Sonepur', 'Odisha', 'Subarnapur', '+916654220100', 'Sonepur Town');


-- Table List Verification
SHOW TABLES;
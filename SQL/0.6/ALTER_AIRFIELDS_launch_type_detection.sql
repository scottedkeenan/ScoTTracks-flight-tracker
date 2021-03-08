ALTER TABLE `airfields` ADD `launch_type_detection` BOOLEAN NOT NULL DEFAULT TRUE AFTER `is_active`;

UPDATE `airfields`
SET `launch_type_detection` = FALSE
WHERE name = 'association-velivole-chateau-arnoux-saint-auban';
ALTER TABLE `airfields` ADD `country` TINYTEXT NULL DEFAULT NULL AFTER `elevation`, ADD `is_active` BOOLEAN NOT NULL DEFAULT TRUE AFTER `country`;


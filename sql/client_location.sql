CREATE TABLE IF NOT EXISTS `ipinfo` (
  `id` int(10) unsigned NOT NULL,
  `countryCode` varchar(2) COLLATE utf8_unicode_ci NOT NULL DEFAULT '',
  `countryName` varchar(32) COLLATE utf8_unicode_ci NOT NULL DEFAULT '',
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
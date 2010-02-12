SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";

DROP TABLE IF EXISTS `listen`;
CREATE TABLE IF NOT EXISTS `listen` (
  `l_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `l_channel` varchar(255) NOT NULL,
  PRIMARY KEY (`l_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 AUTO_INCREMENT=5 ;

DROP TABLE IF EXISTS `status`;
CREATE TABLE IF NOT EXISTS `status` (
  `s_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `s_service` varchar(255) NOT NULL,
  `s_state` varchar(255) NOT NULL DEFAULT 'OK',
  `s_ok` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`s_id`),
  KEY `s_uniqueservice` (`s_service`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 AUTO_INCREMENT=10 ;

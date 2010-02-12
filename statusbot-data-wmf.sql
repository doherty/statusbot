SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";

DROP TABLE IF EXISTS `listen`;
CREATE TABLE IF NOT EXISTS `listen` (
  `l_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `l_channel` varchar(255) NOT NULL,
  PRIMARY KEY (`l_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 AUTO_INCREMENT=5 ;

INSERT INTO `listen` (`l_id`, `l_channel`) VALUES
(1, '#wikimedia-tech'),
(2, '#wikimedia-toolserver'),
(4, '#wikimedia-operations');

DROP TABLE IF EXISTS `status`;
CREATE TABLE IF NOT EXISTS `status` (
  `s_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `s_service` varchar(255) NOT NULL,
  `s_state` varchar(255) NOT NULL DEFAULT 'OK',
  `s_ok` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`s_id`),
  KEY `s_uniqueservice` (`s_service`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 AUTO_INCREMENT=10 ;

INSERT INTO `status` (`s_id`, `s_service`, `s_state`, `s_ok`) VALUES
(1, 'wikis(appservers)', 'OK', 1),
(2, 'wikis(uploads)', 'OK', 1),
(3, 'toolserver(web)', 'OK', 1),
(4, 'toolserver(login)', 'OK', 1),
(5, 'bugzilla', 'OK', 1),
(6, 'wikitech', 'OK', 1),
(7, 'irc.wikimedia.org', 'OK', 1),
(8, 'wikis(squid-cache)', 'OK', 1),
(9, 'misc.', 'OK', 1);


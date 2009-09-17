-- Fix up dept table
alter table dept rename to olddept;

CREATE TABLE `dept` (
      `dept_id` int(11) NOT NULL auto_increment,
      `name` varchar(255) NOT NULL default '',
      `parent` int(11),
      PRIMARY KEY  (`dept_id`),
      UNIQUE KEY `name` (`name`),
      KEY `name_2` (`name`)
) ENGINE=InnoDB ;

insert into dept (dept_id, name) select dept_id, LOWER(REPLACE(name, ' ', '-')) from olddept;

drop table olddept;



-- Attributes
DROP TABLE IF EXISTS attributes;
create table attributes (
    `attr_id`       INTEGER PRIMARY KEY auto_increment,
    `atype`         INTEGER NOT NULL default 0,
    `akey`          VARCHAR(255),
    `data`          TEXT,

    KEY `akey_k` (`akey`)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS attrgroups;
create table attrgroups (
    attrg_id        INTEGER PRIMARY KEY auto_increment,
    attr_ptr        INTEGER NOT NULL default 0,
    attr_id         INTEGER NOT NULL default 0,

    KEY `attr_ptr_k` (`attr_ptr`)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS attrpointer;
create table attrpointer (
    attr_ptr        INTEGER PRIMARY KEY auto_increment
) ENGINE=InnoDB;

alter table realmlinux add column attr_ptr integer default NULL;

-- Fix up dept table to enforce rules on names
-- add attribute pointer here too
alter table dept rename to olddept;

CREATE TABLE `dept` (
      `dept_id` int(11) NOT NULL auto_increment,
      `name` varchar(255) NOT NULL default '',
      `parent` int(11),
      `attr_ptr` integer default NULL,
      PRIMARY KEY  (`dept_id`),
      UNIQUE KEY `name` (`name`),
      KEY `name_2` (`name`)
) ENGINE=InnoDB ;

insert into dept (dept_id, name) select dept_id, LOWER(REPLACE(name, ' ', '-')) from olddept;

drop table olddept;

-- ACLs
DROP TABLE IF EXISTS aclgroups;
create table aclgroups (
    aclg_id     INTEGER PRIMARY KEY auto_increment,
    dept_id     INTEGER not NULL,
    acl_id      INTEGER not NULL,
    perms       INTEGER not NULL,

    KEY `dept_id_k` (`dept_id`)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS acls;
create table acls (
    acl_id      INTEGER PRIMARY KEY auto_increment,
    name        VARCHAR(255) NOT NULL,
    pts         VARCHAR(255) default NULL,
    cell        VARCHAR(255) default NULL
) ENGINE=InnoDB;

DROP TABLE IF EXISTS sysadmins;
create table sysadmins (
    sysadmin_id INTEGER PRIMARY KEY auto_increment,
    acl_id      INTEGER NOT NULL,
    userid      VARCHAR(16),

    KEY `acl_id_k` (`acl_id`),
    KEY `userid_k` (`userid`)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS webkickstartkeys;
create table webkickstartkeys (
    wkk_id      INTEGER PRIMARY KEY auto_increment,
    keyword     VARCHAR(255),

    KEY `keyword_k` (`keyword`)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS sessions;
create table sessions (
    session_id     INTEGER PRIMARY KEY,
    sid            varchar(256) unique not null,
    createtime     float not null,
    timeout        float not null,
    data           text,

    KEY `session_idx` (`sid`)
) ENGINE=InnoDB;


insert into service (name) values ('bcfg2');

-- Test Data
insert into acls (name, pts, cell) values ('admin', 'linux', 'bp');
insert into acls (name, pts, cell) values ('admintest', 'jjneely:webks', 'unity');
insert into acls (name, pts, cell) values ('installer:common', 'installer:common', 'bp');
insert into acls (name, pts, cell) values ('installer:itd-unix', 'installer:itd-unix', 'bp');


insert into webkickstartkeys (keyword) values ('enable.notempclean');
insert into webkickstartkeys (keyword) values ('enable.consolelogin');
insert into webkickstartkeys (keyword) values ('enable.recivemail');
insert into webkickstartkeys (keyword) values ('enable.remotecluster');
insert into webkickstartkeys (keyword) values ('enable.localcluster');
insert into webkickstartkeys (keyword) values ('enable.mailmasq');
insert into webkickstartkeys (keyword) values ('printer');
insert into webkickstartkeys (keyword) values ('cluster');
insert into webkickstartkeys (keyword) values ('dept');
insert into webkickstartkeys (keyword) values ('users');
insert into webkickstartkeys (keyword) values ('root');

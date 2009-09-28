
create table realmlinux (
    host_id     INTEGER PRIMARY KEY auto_increment,
    hostname    VARCHAR(255) not null unique,
    uuid        VARCHAR(40) unique,
    rhnid       INTEGER unique,
    installdate DATETIME not null,
    recvdkey    TINYINT not null,
    dept_id     INTEGER not null,
    version     VARCHAR(32) not null,
    support     TINYINT not null,
    attr_ptr    integer default NULL,

    index(hostname),
    index(uuid),
    foreign key (dept_id) references dept(dept_id)
);

create table hostkeys (
    id          INTEGER PRIMARY KEY auto_increment,
    host_id     INTEGER not null unique,
    publickey   TEXT not null,

    foreign key (host_id) references realmlinux(host_id)
);

create table lastheard (
    lh_id       INTEGER PRIMARY KEY auto_increment,
    host_id     INTEGER not null,
    `timestamp` DATETIME not null,

    foreign key (host_id) references realmlinux(host_id)
);

create table status (
    st_id       INTEGER PRIMARY KEY auto_increment,
    host_id     INTEGER not null,
    service_id  INTEGER not null,
    `timestamp` DATETIME not null,
    received    DATETIME not null,
    success     TINYINT not null,
    data        TEXT,

    index(`timestamp`),
    index(`received`),
    foreign key (host_id) references realmlinux(host_id),
    foreign key (service_id) references service(service_id)
);

create table dept (
    dept_id     INTEGER PRIMARY KEY auto_increment,
    name        VARCHAR(256) not null unique,
    parent      integer default NULL,
    attr_ptr    integer default NULL,

    index(name)
);
insert into dept (name) values ('unknown');

create table service (
    service_id  INTEGER PRIMARY KEY auto_increment,
    name        VARCHAR(256) not null unique,

    index(name)
);

create table rrdqueue (
    q_id        INTEGER PRIMARY KEY auto_increment,
    ds_id       INTEGER not null,
    host_id     INTEGER not null,
    `timestamp` DATETIME not null,
    received    DATETIME not null,
    data        INTEGER,

    index(`timestamp`),
    index(`received`)
);

create table dstype (
    ds_id       INTEGER PRIMARY KEY auto_increment,
    name        VARCHAR(256) not null unique,

    index(name)
);

create table rrdlocation (
    loc_id      INTEGER PRIMARY KEY auto_increment,
    ds_id       INTEGER not null,
    host_id     INTEGER,
    label       VARCHAR(255),
    path        TEXT,

    index(ds_id),
    index(host_id)
);

create table configvalues (
    c_id        INTEGER PRIMARY KEY auto_increment,
    variable    VARCHAR(255),
    value       TEXT,

    index(variable)
);

create table htype (
    htype_id    INTEGER PRIMARY KEY auto_increment,
    name        VARCHAR(256) not null unique,

    index(name)
);

create table history (
    history_id  INTEGER PRIMARY KEY auto_increment,
    htype_id    INTEGER not null,
    host_id     INTEGER,
    `timestamp` DATETIME not null,
    data        TEXT,

    index(`timestamp`),
    foreign key (htype_id) references htype(htype_id)
);

-- Attributes 
create table attributes (
    `attr_id`       INTEGER PRIMARY KEY auto_increment,
    `atype`         INTEGER NOT NULL default 0,
    `data`          TEXT
) ENGINE=InnoDB;

create table attrgroups (
    attrg_id        INTEGER PRIMARY KEY auto_increment,
    attr_ptr        INTEGER NOT NULL default 0,
    attr_id         INTEGER NOT NULL default 0,

    index(attr_ptr)
) ENGINE=InnoDB;

create table attrpointer (
    attr_ptr        INTEGER PRIMARY KEY auto_increment
);

-- ACLs
create table aclgroups (
    aclg_id     INTEGER PRIMARY KEY auto_increment,
    dept_id     INTEGER not NULL,
    acl_id      INTEGER not NULL,
    perms       INTEGER not NULL,

    index(dept_id)
);

create table acls (
    acl_id      INTEGER PRIMARY KEY auto_increment,
    name        VARCHAR(255) NOT NULL,
    pts         VARCHAR(255) default NULL,
    cell        VARCHAR(255) default NULL
);

create table sysadmins (
    sysadmin_id INTEGER PRIMARY KEY auto_increment,
    acl_id      INTEGER NOT NULL,
    userid      VARCHAR(16),

    index(acl_id)
);


-- The following are service types and RRD data source types to collect.
-- The server will record status information of these types.  Adding rows
-- to the tables will allow new status messages, etc to be recorded.

insert into service (name) values ('updates');
insert into service (name) values ('client');
insert into service (name) values ('sysinfo');
insert into service (name) values ('boot');
insert into service (name) values ('usagelog');
insert into service (name) values ('fixit');
insert into service (name) values ('bcfg2');

-- For the RRDTool Queue Handler
insert into dstype (name) values ('master');
insert into dstype (name) values ('usage');
insert into dstype (name) values ('version');
insert into dstype (name) values ('usagesync');

-- For the stored history
insert into htype (name) values ('install_support');
insert into htype (name) values ('install_nosupport');
insert into htype (name) values ('blessing');

-- Use python rlmtools/configDragon.py to manage the advanced configuration
-- stored inside the database.


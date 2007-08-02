
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


-- The following are service types and RRD data source types to collect.
-- The server will record status information of these types.  Adding rows
-- to the tables will allow new status messages, etc to be recorded.

insert into service (name) values ('updates');
insert into service (name) values ('client');
insert into service (name) values ('sysinfo');
insert into service (name) values ('boot');
insert into service (name) values ('usagelog');

-- For the RRDTool Queue Handler
insert into dstype (name) values ('usage');

-- For the stored history
insert into htype (name) values ('install_support');
insert into htype (name) values ('install_nosupport');
insert into htype (name) values ('blessing');

-- Use python rlmtools/configDragon.py to manage the advanced configuration
-- stored inside the database.


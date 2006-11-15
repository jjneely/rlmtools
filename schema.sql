
create table realmlinux (
    host_id     INTEGER PRIMARY KEY auto_increment,
    hostname    VARCHAR(255) not null unique,
    installdate DATETIME not null,
    recvdkey    TINYINT not null,
    publickey   TEXT,
    dept_id     INTEGER not null,
    version     VARCHAR(32) not null,
    support     TINYINT not null,

    index(hostname),
    foreign key (dept_id) references dept(dept_id)
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
    success     TINYINT not null,
    data        TEXT,

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


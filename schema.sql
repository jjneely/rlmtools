
create table realmlinux (
    host_id     INTEGER PRIMARY KEY auto_increment,
    hostname    VARCHAR(255) not null unique,
    installdate DATETIME not null,
    recvdkey    TINYINT not null,
    publickey   TEXT,
    dept        VARCHAR(32) not null,
    version     VARCHAR(32) not null,
    support     TINYINT not null
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
    service     VARCHAR(255) not null,
    `timestamp` DATETIME not null,
    success     TINYINT not null,
    data        TEXT,

    foreign key (host_id) references realmlinux(host_id)
);


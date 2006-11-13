
CREATE TABLE realmlinux (
    host_id     INTEGER PRIMARY KEY auto_increment,
    hostname    VARCHAR(255),
    installdate DATETIME,
    recvdkey    TINYINT,
    publickey   TEXT,
    dept        VARCHAR(32),
    version     VARCHAR(32),
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


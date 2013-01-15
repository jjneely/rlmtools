DROP TABLE IF EXISTS puppetrepos;
create table puppetrepos (
    p_id        INTEGER PRIMARY KEY auto_increment,
    path        VARCHAR(1024) not null,
    dept_id     INTEGER,

    index(path)
);

DROP TABLE IF EXISTS webkickstartdirs;
create table webkickstartdirs (
    wkd_id      INTEGER PRIMARY KEY auto_increment,
    path        VARCHAR(1024) not null,
    dept_id     INTEGER,

    index(path)
);

DROP TABLE IF EXISTS rhnprotectedusers;
create table rhnprotectedusers (
    id          INTEGER PRIMARY KEY auto_increment,
    userid      VARCHAR(256) not null unique,

    index(userid)
);

insert into rhnprotectedusers (userid) values ('tkl-admin');
insert into rhnprotectedusers (userid) values ('slack');
insert into rhnprotectedusers (userid) values ('ece-scripts');

DROP TABLE IF EXISTS rhngroups;
create table rhngroups (
    rg_id       INTEGER PRIMARY KEY auto_increment,
    dept_id     INTEGER,
    rhng_id     INTEGER not null,
    rhnname     VARCHAR(1024) not null
);


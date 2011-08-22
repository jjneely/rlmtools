create table webkickstartdirs (
    wkd_id      INTEGER PRIMARY KEY auto_increment,
    path        VARCHAR(1024) not null,
    dept_id     INTEGER,

    index(path)
);

create table rhngroups (
    rg_id       INTEGER PRIMARY KEY auto_increment,
    dept_id     INTEGER,
    rhng_id     INTEGER not null,
    rhnname     VARCHAR(1024) not null
);


create table webkickstartdirs (
    wkd_id      INTEGER PRIMARY KEY auto_increment,
    path        VARCHAR(1024) not null,
    dept_id     INTEGER,

    index(path)
);


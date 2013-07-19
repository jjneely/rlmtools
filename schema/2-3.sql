create table profilekeys (
    pro_id      INTEGER PRIMARY KEY auto_increment,
    keyword     VARCHAR(255),

    index(keyword)
);

insert into profilekeys (keyword) values ("owner");
insert into profilekeys (keyword) values ("root");
insert into profilekeys (keyword) values ("user");
insert into profilekeys (keyword) values ("enable.activationkey");


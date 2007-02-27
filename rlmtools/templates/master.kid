<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml"  xmlns:py="http://purl.org/kid/ns#">

<head py:match="item.tag=='{http://www.w3.org/1999/xhtml}head'">
  <title>Realm Linux Management Tools</title>

  <link rel="stylesheet" type="text/css" 
    href="http://itd.ncsu.edu/itd-branding/styles/itd_top_nav_iframe.css" /> 

  <style type="text/css">
    h1 {
       clear: both;
    }
    h2 {
       clear: both;
    }
    h2.space {
       clear: both;
       padding-top: 20px;
    }  
    A {
       text-decoration: none;
       color: #000088;
    }
    a:hover {
       text-decoration: underline;
    }
    div.content {
       font-family: Arial,Helvetica,Sans-Serif;
       padding: 1em;
    }
    div.alert {
       float: left;
       width: 20em;
       background-color: #cc0000;
       padding: 0.5em;
       border: 4px solid #ff6666;
    }
    div.alert p {
       color: #ffffff;
    }
    div.altert b {
       font-weight: bold;
       color: #ffffff;
    }
    div.category {
       clear: left;
       text-align: center;
    }
    div.field {
       margin: 1.0px;
       border: 1.0px solid #000000;
       vertical-align: middle;
       text-align: center;
       font-weight: bold;
       float: left;
       width: 6em;
       height: 1.5em;
       background-color: #ececec;
    }
    div.field:hover
    {
       background-color: #cccccc
    }
    div.field A {
       text-decoration: none;
       color: blue;
    }
    div.field A:hover {
       text-decoration: underline;
    }
    div.good {
       margin: 1.0px;
       border: 1.0px solid #000000;
       vertical-align: middle;
       text-align: center;
       font-weight: bold;
       float: left;
       width: 25em; 
       height: 1.5em;
       background-color: #99ff99;
    }
    div.good:hover {
       background-color: #66ff66;
    }
    div.good A {
       text-decoration: none;
       color: black;
    }
    div.good A:hover {
       text-decoration: underline;
    }
    div.bad {
       margin: 1.0px;
       border: 1.0px solid #000000;
       vertical-align: middle;
       text-align: center;
       font-weight: bold;
       float: left;
       width: 25em;
       height: 1.5em;
       background-color: #ff0000;
    }
    div.bad:hover {
       background-color: #aa0000;
    }
    div.bad A {
       text-decoration: none;
       color: #fbfbfb;
    }
    div.bad A:hover {
       text-decoration: underline;
    }
    table {
       margin-left: auto;
       margin-right: auto;   
       border-style: solid;
       border-color: gray;
       border-width: 1px;
    }
    td {
       padding: 4px;
       border-style: none;
    }
    th {
       padding: 4px;
       border-style: none;
       border-bottom-style: solid;
       border-bottom-width: 1px;
       border-bottom-color: gray;
    }
    th.right {
       text-align: right;
       border-bottom-style: none;
       border-right-width: 1px;
       border-right-color: gray;
       border-right-style: solid;
    }
    tr.good {
       background-color: #99ff99;
    }
    tr.good:hover {
       background-color: #66ff66;
    }
    tr.neutral {
       background-color: #ececec;
    }
    tr.neutral:hover {
       background-color: #cccccc;
    }
    tr.bad {
       background-color: #ff0000;
       color: #ffffff;
    }
    tr.bad:hover {
       background-color: #aa0000;
       color: #ffffff;
    }
    tr.good A {
       text-decoration: none;
       color: #000088;
    }
    tr.neutral A {
       text-decoration: none;
       color: #000088;
    }
    tr.bad A {
       text-decoration: none;
       color: white;
    }
    tr A:hover {
       text-decoration: underline;
    }
  </style>

  <meta py:replace="item[:]" />

</head>
<body py:match="item.tag=='{http://www.w3.org/1999/xhtml}body'">

  <iframe name="ITDNav" id="ITDNav" 
    src="http://itd.ncsu.edu/itd-branding/itd_nav.php?color=black" 
    scrolling="no" title="itd-nav-bar">  
    Your browser does not support inline frames or is currently configured  
    not to display inline frames.<br /> 
    Visit <a href="http://itd.ncsu.edu/">http://itd.ncsu.edu</a>.
  </iframe>

  <div class="content">

  <h1>Realm Linux Management</h1>

  <div py:content="item[:]" />

  </div>

</body>

</html>


<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml"  xmlns:py="http://purl.org/kid/ns#">

<head py:match="item.tag=='{http://www.w3.org/1999/xhtml}head'">
  <title>Realm Linux Management Tools</title>

  <link rel="stylesheet" type="text/css" 
    href="http://itd.ncsu.edu/itd-branding/styles/itd_top_nav_iframe.css" /> 

  <style type="text/css">
    h1 {
       clear: left;
    }
    h2 {
       clear: left;
    }  
    div.content {
       font-family: Arial,Helvetica,Sans-Serif;
       padding: 1em;
    }
    div.category {
       clear: both;
       text-align: center;
       padding-bottom: 1.5em;
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
    div.field:hover {
       background-color: #cccccc
    }
    div.field A {
       text-decoration: none;
       color: blue;
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
       background-color: #77ff77
    }
    div.good A {
       text-decoration: none;
       color: black;
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

  <p>Within this tool you will find all Realm Linux clients from RL 3 and
    above that are at least quasi-functional.  These pages are to help you
    identify clients that may not be functioning correctly and to tell you
    what may be wrong.  Clients are divided up into Departments.</p>

  <div py:content="item[:]" />

  </div>

</body>

</html>


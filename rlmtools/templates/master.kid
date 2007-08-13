<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml"  xmlns:py="http://purl.org/kid/ns#">

<head py:match="item.tag=='{http://www.w3.org/1999/xhtml}head'">
  <title>Realm Linux Management Tools</title>

  <link rel="stylesheet" type="text/css" 
    href="/rlmtools/static/css/navbar.css" /> 
  <link rel="stylesheet" type="text/css" 
    href="/rlmtools/static/css/common.css" /> 

  <meta py:replace="item[:]" />

</head>
<body py:match="item.tag=='{http://www.w3.org/1999/xhtml}body'">

<div class="itdnavbar">
  <div class="itd_logo">
      <a href="http://www.itd.ncsu.edu/"><img alt="ITD Homepage"
          src="/rlmtools/static/itd_logo.gif"/></a></div>
  <div class="ncsu_brick">
      <a href="http://www.ncsu.edu/"><img src="/rlmtools/static/brick_black.gif"
          alt="NC State University"/></a></div>
  <div class="itdcontainer">
    <ul>
      <li><a href="http://itd.ncsu.edu">Information Technology Division</a>
        &nbsp;|&nbsp;</li>
      <li><a href="http://sysnews.ncsu.edu">SysNews</a>
        &nbsp;|&nbsp;</li>
      <li><a href="http://www.linux.ncsu.edu">Campus Linux Services</a>
        &nbsp;|&nbsp;</li>
      <li><a href="http://help.ncsu.edu">NC State Help Desk</a></li>
    </ul>
  </div>
</div>

  <ul class="makemenu">
    <li class="title">Liquid Dragon Menu</li>
    <li><a href="/rlmtools">Front Page</a></li>
    <li><a href="/rlmtools/notregistered">Web-Kickstarting</a></li>
    <li><a href="/rlmtools/problems">Problem Clients</a></li>
    <li><a href="/rlmtools/versionList">Version List</a></li>
    <li><a href="/rlmtools/noupdates">Not Running Updates</a></li>
    <li py:for="name, href in value_of('backlinks', [])">
      <a href="" py:attrs="'href':href" py:content="name">Backwards</a>
    </li>
  </ul>

  <div class="content">

  <h1>Realm Linux Management - Project Liquid Dragon</h1>

  <div py:content="item[:]" />

  </div>

</body>

</html>


<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml"  xmlns:py="http://purl.org/kid/ns#"
  py:extends="'master.kid'">

<head>
  <title>Realm Linux Management Tools</title>
  <meta content="text/html; charset=UTF-8" http-equiv="content-type" 
    py:replace="''"/>
  <link rel="stylesheet" type="text/css" 
    href="http://itd.ncsu.edu/itd-branding/styles/itd_top_nav_iframe.css" /> 
</head>
<body>

  <h2>Client Statistics</h2>
  <ul>
    <li>Clients Currently Checking In: <span py:replace="active">-3</span></li>
    <li>Supported Clients: <span py:replace="supported">-3</span></li>
    <li>Non-Supported Clients: <span py:replace="notsupported">-4</span></li>
    <li>Clients Not Registered: <a href="notregistered" 
                                  py:content="notregistered">-5</a></li>
  </ul>

  <h2>Departments</h2>

  <div class="category">
    <div class="field"
      py:for="dept in departments">
      <a href="/dept"
        py:attrs="'href':dept['url']"
        py:content="dept['name']">Your Department Here</a>
    </div>
  </div>

  <br />

  <h2 class="space">Tools</h2>

  <p>Other tools may appear here in the future.</p>

</body>

</html>


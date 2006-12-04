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

  <p>Welcome <span py:replace="name"/>.</p>

  <h2>Client Statistics</h2>
  <table>
    <tr class="neutral">
      <th class="right">Clients Currently Checking In:</th>
      <td py:content="active">-1</td>
    </tr>
    <tr class="neutral">
      <th class="right">Supported Clients:</th>
      <td py:content="supported">-1</td>
    </tr>
    <tr class="neutral">
      <th class="right">Non-Supported Clients:</th>
      <td py:content="notsupported">-1</td>
    </tr>
    <tr class="neutral">
      <th class="right">Clients Not Registered:</th>
      <td><a href="notregistered" py:content="notregistered">-1</a></td>
    </tr>
  </table>

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


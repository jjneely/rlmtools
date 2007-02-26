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

  <p>Within this tool you will find all Realm Linux clients from RL 3 and
    above that are at least quasi-functional.  These pages are to help you
    identify clients that may not be functioning correctly and to tell you
    what may be wrong.  Clients are divided up into Departments.</p>

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

  <table>
    <tr class="neutral">
      <th>Department Name</th><th>Supported RL Clients</th>
      <th>Unsupported RL Clients</th>
    </tr>
    <tr class="neutral" py:for="dept in departments">
      <td><a href="dept" py:attrs="'href':dept['url']"
                         py:content="dept['name']">Your Department Here</a>
      </td>
      <td py:content="dept['supported']" />
      <td py:content="dept['unsupported']" />
    </tr>
  </table>

  <h2 class="space">Tools</h2>

  <p>Other tools may appear here in the future.</p>

</body>

</html>


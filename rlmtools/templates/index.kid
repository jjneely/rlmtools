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
      <td py:content="totals['supported']">-1</td>
    </tr>
    <tr class="neutral">
      <th class="right">Non-Supported Clients:</th>
      <td py:content="totals['unsupported']">-1</td>
    </tr>
    <tr class="neutral">
      <th class="right">Total Clients:</th>
      <td py:content="totals['unsupported'] + totals['supported']">-1</td>
    </tr>
    <tr class="neutral">
      <th class="right">Web-Kickstarting:</th>
      <td><a href="notregistered" 
             py:content="totals['webkickstarting']">-1</a></td>
    </tr>
    <tr class="neutral">
      <th class="right">Clients Reporting Problems:</th>
      <td><a href="problems" 
          py:content="totals['problems']">-1</a></td>
    </tr>
    <tr class="neutral">
      <th class="right">Not Receiving Updates:</th>
      <td><a href="noupdates" 
          py:content="totals['noupdates']">-1</a></td>
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
      <td><a href="dept" py:attrs="'href':dept['url']"
                         py:content="dept['supported']" />
      </td>
      <td><a href="dept" py:attrs="'href':dept['url']"
                         py:content="dept['unsupported']" />
      </td>
    </tr>
  </table>

  <h2 class="space">Tools</h2>

  <p>Other tools may appear here in the future.</p>

</body>

</html>


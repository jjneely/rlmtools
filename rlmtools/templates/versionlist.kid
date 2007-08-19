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

  <p>The Version List shows the number of all known Realm Linux clients per
    Realm Linux version.  Links are provided to list out the individual
    clients.  This may help in tracking down old or unsupported versions
    that are currently deployed.</p>

  <h2 style="clear:none;">Version List</h2>

  <table class="noborder">
    <tr><td>
        <img src="/rlmtools/static/graphs/versions-3d.png"/>
    </td>
    <td>

  <table>
    <tr class="neutral">
      <th>Realm Linux Version</th>
      <th># of Clients</th>
    </tr>
    <tr class="neutral" py:for="version in versions">
      <td py:content="version['version']">Realm Linux 33 1/3</td>
      <td><a href="/rlmtools/versionIndex?version=${version['version']}" 
          py:content="version['count']">-1</a></td>
    </tr>
  </table>

  </td>
  </tr></table>

</body>

</html>


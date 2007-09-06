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

  <p>Usage is the time a realm user spent logged into a 
    Realm Linux machine either locally or remotely.  Usage information
    is reported asynchronously by each client and therefore may not
    be accurate for the last 24 to 72 hours.  Click on a graph to
    see more detail.</p>

  <p>Usage reporting is a feature of Realm Linux 5.  Usage from any
    previous Realm Linux versions is not included.</p>

  <h2>Usage Statistics</h2>

  <table class="noborder">
    <tr class="neutral" py:for="graph in graphs">
      <td py:content="graph['summary']"/>
      <td py:if="graph['url'] != ''">
        <a href="" py:attrs="'href':graph['href']">
          <img src="" py:attrs="'src':graph['url']"/>
        </a>
      </td>
      <td py:if="graph['url'] == ''">
        No graph data available.
      </td>
    </tr>
  </table>

</body>

</html>


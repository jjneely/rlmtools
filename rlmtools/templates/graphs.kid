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

  <h2 py:content="title">Foo Bar</h2>

  <table>
    <tr class="neutral" py:for="graph in graphs">
      <td py:content="graph['summary']">Summary text</td>
      <td py:if="graph['url'] != ''">
        <img src="" py:attrs="'src':graph['url']"/>
      </td>
      <td py:if="graph['url'] == ''">
        No graph data available.
      </td>
    </tr>
  </table>

</body>

</html>


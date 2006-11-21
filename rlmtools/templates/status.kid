<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml"  xmlns:py="http://purl.org/kid/ns#"
  py:extends="'master.kid'">

<head>
  <title>Realm Linux Management Tools</title>
</head>
<body>

  <p>Return to:
    <ul>
      <li><a href="" py:attrs="'href':backurl">Client Detail</a></li>
    </ul>
  </p>

  <h1>Client Status: <span py:replace="status['hostname']" /></h1>

  <p>Below are the full details of a specific status entry for this host.
    Remember to check the latest status entry for any errors that you see.
    Note that clients queue up messages to report.  There may be a few hours
    difference between the Client Time Stamp and the Received Time Stamp.
    The Client Time Stamp is directly reported by the client so it will
    also be affected if the client's clock isn't set properly.
  </p>

  <table>
    <tr class="neutral">
      <th class="right">Hostname:</th>
      <td py:content="status['hostname']">foo.ncsu.edu</td>
    </tr>
    <tr class="neutral">
      <th class="right">Service Name:</th>
      <td py:content="status['name']">foo</td>
    </tr>
    <tr class="neutral">
      <th class="right">Client Time Stamp:</th>
      <td py:content="status['timestamp']">foo</td>
    </tr>
    <tr class="neutral">
      <th class="right">Received Time Stamp:</th>
      <td py:content="status['received']">The Epoch</td>
    </tr>
    <tr py:attrs="'class':status['success'] and 'good' or 'bad'">
      <th class="right">Success:</th>
      <td py:content="status['success'] and 'Good' or 'Bad'">foobared</td>
    </tr>

    <tr py:attrs="'class':status['data_class']">
      <th class="right">Message:</th>
      <td>
        <pre py:content="status['data']">The Epoch</pre>
      </td>
    </tr>
  </table>

</body>

</html>


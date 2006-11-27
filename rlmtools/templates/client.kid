<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml"  xmlns:py="http://purl.org/kid/ns#"
  py:extends="'master.kid'">

<head>
  <title>Realm Linux Management Tools</title>
</head>
<body>

  <p>Return to:
    <ul>
      <li><a href="" py:attrs="'href':backurl">Client Listing</a></li>
    </ul>
  </p>

  <h1>Client Status: <span py:replace="client['hostname']" /></h1>

  <p>All Realm Linux clients phone home to report status information in
    several ways.  This table lists out the status information we know
    about from the last 30 days.  If this client is red or listed as
    not supported the error messages may contain clues as to why this
    client may be malfunctioning.</p>

  <table>
    <tr class="neutral">
      <th class="right">Hostname:</th>
      <td py:content="client['hostname']">foo.ncsu.edu</td>
    </tr>
    <tr class="neutral">
      <th class="right">Realm Linux Version:</th>
      <td py:content="client['version']">foo</td>
    </tr>
    <tr class="neutral">
      <th class="right">Department:</th>
      <td py:content="client['dept']">The Epoch</td>
    </tr>
    <tr py:attrs="'class':client['support'] and 'good' or 'bad'">
      <th class="right">Support:</th>
      <td py:content="client['support'] and 'Yes' or 'No'">foobared</td>
    </tr>
    <tr py:attrs="'class':client['recvdkey'] and 'good' or 'bad'">
      <th class="right">Received RSA Key:</th>
      <td py:content="client['recvdkey'] and 'Yes' or 'No'">foobared</td>
    </tr>
    <tr class="neutral">
      <th class="right">Install Date:</th>
      <td py:content="client['installdate']">The Epoch</td>
    </tr>
    <tr py:attrs="'class':client['lastcheck_good'] and 'good' or 'bad'">
      <th class="right">Last Heard From:</th>
      <td py:content="client['lastcheck']">The Epoch</td>
    </tr>
  </table>

  <p></p>

  <table>
    <tr class="neutral">
      <th>Service</th>
      <th>Success</th>
      <th>Client Time Stamp</th>
      <th>Message Received Stamp</th>
      <th>Message</th>
    </tr>
    <tr py:for="stat in status" py:attrs="'class':stat['class']">
      <td py:content="stat['service']">Bob</td>
      <td py:content="stat['success'] and 'Good' or 'Bad'">Schwank</td>
      <td py:content="stat['timestamp']">Time Stamp</td>
      <td py:content="stat['received']">Reviced Stamp</td>
      <td>
        <a href="" py:attrs="'href':stat['url']" py:content="stat['summary']">
        </a>
      </td>
    </tr>
  </table>
      
</body>

</html>

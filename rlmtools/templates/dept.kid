<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml"  xmlns:py="http://purl.org/kid/ns#"
  py:extends="'master.kid'">

<head>
  <title>Realm Linux Management Tools</title>
</head>
<body>

  <h1>Client List: <span py:replace="department" /></h1>

  <p>Clients are categorized into Supported and Non-Supported.  A Supported
    client is configured with Web-Kickstart and <i>may</i> meet the
    requirements for official support.  Non-Supported clients are unknown
    clients.  Its possible that something has happened to a supported
    client to make it lose its supported status such as removing the
    client's config file from AFS, hostname changes, etc.</p>

  <h2>Supported</h2>

  <div class="category">
    <div py:for="client in support"
      class="${client['status'] and 'good' or 'bad'}">
      <a py:attrs="'href':client['url']"
        py:content="client['hostname']">Your Client</a>
    </div>
  </div>

  <p py:if="len(support) == 0">
    No supported clients in database.
  </p>

  <p></p>
  <h2>Non-Supported</h2>

  <div class="category">
    <div py:for="client in nosupport"
      class="${client['status'] and 'good' or 'bad'}">
      <a py:attrs="'href':client['url']"
        py:content="client['hostname']">Your Client</a>
    </div>
  </div>

  <p py:if="len(nosupport) == 0">
    No non-supported clients in database.
  </p>


</body>

</html>


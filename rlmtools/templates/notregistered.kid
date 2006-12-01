<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml"  xmlns:py="http://purl.org/kid/ns#"
  py:extends="'master.kid'">

<head>
  <title>Realm Linux Management Tools</title>
</head>
<body>

  <p>Return to:
    <ul>
      <li><a href="" py:attrs="'href':backurl">Department Listing</a></li>
    </ul>
  </p>

  <h1>Client List: <span py:replace="department" /></h1>

  <p>These clients have been entered into the database by Web-Kickstart
    but have not uploaded their RSA key.  Clients must register within
    24 hours of installation.  This normally happens withing 4 hours if
    the machine is running normally.  Clients may be registered manually
    provided that you have access to its Web-Kickstart config directory,
    login as your user and run the <tt>ncsubless</tt> command.</p>

  <h2>Supported: <span py:replace="len(support)"/> Clients</h2>

  <div class="category">
    <div py:for="client in support"
      class="${client['status'] and 'good' or 'bad'}">
      <a py:attrs="'href':client['url']"
        py:content="client['hostname']">Your Client</a>
    </div>
  </div>

  <p></p>
  <h2 class="space">Non-Supported: <span py:replace="len(nosupport)"/> Clients</h2>

  <div class="category">
    <div py:for="client in nosupport"
      class="${client['status'] and 'good' or 'bad'}">
      <a py:attrs="'href':client['url']"
        py:content="client['hostname']">Your Client</a>
    </div>
  </div>

</body>

</html>


<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml"  xmlns:py="http://purl.org/kid/ns#"
  py:extends="'master.kid'">

<head>
  <title>Realm Linux Management Tools</title>
</head>
<body>

  <p>The following clients, listed by department, are not receiving updates
     and security errata.  These clients may be turned off or otherwise
     prevented from communicating with RHN or their Yum repositories.
     Each client should contain
     some 'update' error messages that we can use to find the problem.
     These should be corrected as soon as possible.
  </p>

  <div py:for="dept in departments">

    <h2 class="space">Department: <span py:replace="dept"/></h2>

    <div class="category">
      <div py:for="client in clients[dept]" class="bad">
        <a py:attrs="'href':client['url']"
          py:content="client['hostname']">Your Client</a>
      </div>
    </div>

  </div>

  <p py:if="len(clients) == 0">
    No clients reporting problems.
  </p>

</body>

</html>


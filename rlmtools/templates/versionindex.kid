<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml"  xmlns:py="http://purl.org/kid/ns#"
  py:extends="'master.kid'">

<head>
  <title>Realm Linux Management Tools</title>
</head>
<body>

  <p>This is a list of all known Realm Linux clients with a given
    version sorted by department.
  </p>

  <table>
    <tr class="neutral">
      <th class="right">Realm Linux Version:</th>
      <td py:content="version">-1</td>
    </tr>
    <tr class="neutral">
      <th class="right">Number of Clients:</th>
      <td py:content="count">-1</td>
    </tr>
    <tr class="neutral">
      <th class="right">Number of Departments:</th>
      <td py:content="len(departments)">-1</td>
    </tr>
  </table>

  <div py:for="dept in departments">

    <h2 class="space">Department: <span py:replace="dept"/></h2>

    <div class="category">
      <div py:for="client in clients[dept]" 
        class="${client['status'] and 'good' or 'bad'}">
        <a py:attrs="'href':client['url']"
          py:content="client['hostname']">Your Client</a>
      </div>
    </div>

  </div>

  <p py:if="len(clients) == 0">
    No known clients with this version.
  </p>

</body>

</html>


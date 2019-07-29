from ldap3 import Server, Connection, ALL, NTLM
from ldap3.core.exceptions import LDAPBindError


def ldap_login(username, password):
    userdn = "CN=" + username + ",OU=测试团队,OU=研发部,OU=产品研发中心,OU=Sijibao,DC=sijibao,DC=com"
    server = Server("172.31.255.250", get_info=ALL)
    try:
        conn = Connection(server, userdn, password, auto_bind=True)
        print(conn.extend.standard.who_am_i())
        #a = conn.search('DC=sijibao,DC=com', '(objectclass=person)')
        #print(len(conn.entries))
        return conn.bind()
    except LDAPBindError:
        return False

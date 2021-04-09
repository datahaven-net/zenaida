available = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
  <command>
    <check>
      <contact:check
        xmlns:contact="urn:ietf:params:xml:ns:contact-1.0">
        <contact:id>%(handle)s</contact:id>
      </contact:check>
     </check>
    <clTRID>ABC-12345</clTRID>
  </command>
</epp>"""

create = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0" xmlns:sidn-ext-epp="http://rxsd.domain-registry.nl/sidn-ext-epp-1.0">
  <command>
    <create>
      <contact:create
       xmlns:contact="urn:ietf:params:xml:ns:contact-1.0">
        <contact:id>sh8013</contact:id>
        <contact:postalInfo type="loc">
          <contact:name>%(name)s</contact:name>
          <contact:org>%(org)s</contact:org>
          <contact:addr>
            <contact:street>%(street)s</contact:street>
            <contact:city>%(city)s</contact:city>
            <contact:sp>%(sp)s</contact:sp>
            <contact:pc>%(pc)s</contact:pc>
            <contact:cc>%(cc)s</contact:cc>
          </contact:addr>
        </contact:postalInfo>
        <contact:voice>%(voice)s</contact:voice>
        <contact:fax>%(fax)s</contact:fax>
        <contact:email>%(email)s</contact:email>
        <contact:authInfo>
          <contact:pw>2fooBAR</contact:pw>
        </contact:authInfo>
      </contact:create>
    </create>
    <extension>
      <sidn-ext-epp:ext>
        <sidn-ext-epp:create>
          <sidn-ext-epp:contact>
            <sidn-ext-epp:legalForm>BV</sidn-ext-epp:legalForm>
            <sidn-ext-epp:legalFormRegNo>8764654.0</sidn-ext-epp:legalFormRegNo>
          </sidn-ext-epp:contact>
        </sidn-ext-epp:create>
      </sidn-ext-epp:ext>
    </extension>
  <clTRID>ABC-12345</clTRID>
  </command>
</epp>"""

info = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
  <command>
    <info>
      <contact:info
       xmlns:contact="urn:ietf:params:xml:ns:contact-1.0">
        <contact:id>%(handle)s</contact:id>
      </contact:info>
    </info>
    <clTRID>ABC-12345</clTRID>
  </command>
</epp>"""

update = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
  <command>
    <update>
    <contact:update
     xmlns:contact="urn:ietf:params:xml:ns:contact-1.0">
      <contact:id>%(handle)s</contact:id>
        <contact:chg>
          <contact:postalInfo type="loc">
            <contact:name>%(name)s</contact:name>
            <contact:org>%(org)s</contact:org>
            <contact:addr>
              <contact:street>%(street)s</contact:street>
              <contact:city>%(city)s</contact:city>
              <contact:pc>%(pc)s</contact:pc>
              <contact:cc>%(cc)s</contact:cc>
            </contact:addr>
          </contact:postalInfo>
          <contact:voice>%(voice)s</contact:voice>
          <contact:fax>%(fax)s</contact:fax>
          <contact:email>%(email)s</contact:email>
        </contact:chg>
      </contact:update>
    </update>
    <clTRID>ABC-12345</clTRID>
  </command>
</epp>"""
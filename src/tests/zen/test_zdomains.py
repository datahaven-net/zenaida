from zen import zdomains

def test_domain_is_valid():
    assert zdomains.is_valid('test.com') is True

def test_domain_is_not_valid():
    assert zdomains.is_valid('-not-valid-domain-.com') is False

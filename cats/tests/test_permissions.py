import pytest

from cats.api.permissions import IsOwnerOrAdmin

class FakeUser:
    def __init__(self,is_staff=False):
        self.is_staff = is_staff

class FakeObject:
    def __init__(self,user):
        self.user = user

class FakeRequest:
    def __init__(self, user):
        self.user = user

@pytest.mark.parametrize(
        "is_owner, is_admin, should_be_allowed",
        [(True,False, True),
         (False, True, True),
         (False, False, False),
         (True,True, True)]
)
def test_is_owner_or_admin(is_owner, is_admin, should_be_allowed):
    request_user = FakeUser(is_staff=is_admin)
    request = FakeRequest(user=request_user)
    object_user = request_user if is_owner else FakeUser()
    object = FakeObject(user=object_user)

    assert should_be_allowed == IsOwnerOrAdmin().has_object_permission(request=request, obj=object, view= None)

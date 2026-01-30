import pytest

from accounts.models import CustomUser

# Create your tests here.

@pytest.mark.django_db
def test_model_custom_user_create_user():
    email="test@email.com"
    password="testpassword"
    user = CustomUser.objects.create_user(email=email,password=password)

    assert user.email == email
    assert user.password is not None
    assert user.password is not password
    assert not user.is_staff
    assert not user.is_superuser

@pytest.mark.django_db
def test_model_custom_user_create_superuser():
    email="test@email.com"
    password="testpassword"
    user = CustomUser.objects.create_superuser(email=email,password=password)

    assert user.email == email
    assert user.password is not None
    assert user.password is not password
    assert user.is_staff
    assert user.is_superuser

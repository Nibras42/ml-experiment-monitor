import pytest
import factory
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        self.set_password(extracted if extracted is not None else 'TestPass123!')
        self.save()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


# --- Model tests ---

@pytest.mark.django_db
class TestUserModel:
    def test_str_returns_email(self):
        user = UserFactory()
        assert str(user) == user.email

    def test_uuid_primary_key(self):
        user = UserFactory()
        assert user.pk is not None
        assert len(str(user.pk)) == 36  # UUID format

    def test_timestamps_are_set(self):
        user = UserFactory()
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_full_name_property(self):
        user = UserFactory(first_name='Ada', last_name='Lovelace')
        assert user.full_name == 'Ada Lovelace'

    def test_full_name_strips_blank_parts(self):
        user = UserFactory(first_name='', last_name='')
        assert user.full_name == ''

    def test_create_superuser(self):
        superuser = User.objects.create_superuser(email='admin@example.com', password='Admin123!')
        assert superuser.is_staff is True
        assert superuser.is_superuser is True


# --- Register endpoint ---

@pytest.mark.django_db
class TestRegisterView:
    url = '/api/users/register/'

    def test_register_success(self, client):
        payload = {
            'email': 'new@example.com',
            'password': 'StrongPass123!',
            'first_name': 'Test',
            'last_name': 'User',
        }
        response = client.post(self.url, payload, format='json')
        assert response.status_code == 201
        assert response.data['email'] == 'new@example.com'
        assert 'password' not in response.data
        assert User.objects.filter(email='new@example.com').exists()

    def test_register_duplicate_email(self, client, user):
        payload = {'email': user.email, 'password': 'StrongPass123!'}
        response = client.post(self.url, payload, format='json')
        assert response.status_code == 400

    def test_register_missing_email(self, client):
        response = client.post(self.url, {'password': 'StrongPass123!'}, format='json')
        assert response.status_code == 400

    def test_register_missing_password(self, client):
        response = client.post(self.url, {'email': 'x@example.com'}, format='json')
        assert response.status_code == 400

    def test_register_weak_password(self, client):
        payload = {'email': 'x@example.com', 'password': '123'}
        response = client.post(self.url, payload, format='json')
        assert response.status_code == 400

    def test_register_invalid_email_format(self, client):
        payload = {'email': 'not-an-email', 'password': 'StrongPass123!'}
        response = client.post(self.url, payload, format='json')
        assert response.status_code == 400


# --- Login endpoint ---

@pytest.mark.django_db
class TestLoginView:
    url = '/api/users/login/'

    def test_login_success(self, client, user):
        response = client.post(self.url, {'email': user.email, 'password': 'TestPass123!'}, format='json')
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_login_wrong_password(self, client, user):
        response = client.post(self.url, {'email': user.email, 'password': 'wrongpassword'}, format='json')
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post(self.url, {'email': 'nobody@example.com', 'password': 'pass'}, format='json')
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        response = client.post(self.url, {}, format='json')
        assert response.status_code == 400


# --- Token refresh endpoint ---

@pytest.mark.django_db
class TestTokenRefreshView:
    url = '/api/users/token/refresh/'

    def test_refresh_success(self, client, user):
        refresh = str(RefreshToken.for_user(user))
        response = client.post(self.url, {'refresh': refresh}, format='json')
        assert response.status_code == 200
        assert 'access' in response.data

    def test_refresh_invalid_token(self, client):
        response = client.post(self.url, {'refresh': 'invalidtoken'}, format='json')
        assert response.status_code == 401


# --- Me endpoint ---

@pytest.mark.django_db
class TestMeView:
    url = '/api/users/me/'

    def test_me_authenticated(self, auth_client, user):
        response = auth_client.get(self.url)
        assert response.status_code == 200
        assert response.data['email'] == user.email
        assert response.data['id'] == str(user.pk)

    def test_me_unauthenticated(self, client):
        response = client.get(self.url)
        assert response.status_code == 401

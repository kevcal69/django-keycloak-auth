from django.test import TestCase, Client, RequestFactory
from rest_framework import status
from django.conf import settings
from .middleware import KeycloakMiddleware, KeycloakConnect
from core import views
from unittest.mock import Mock

class KeycloakMiddlewareTestCase(TestCase):

    # Fixture prerequisites to run the tests
    # fixtures = ['banks']
    
    def setUp(self):
        self.uri = '/core/banks'
        self.client = Client()
        self.factory = RequestFactory()

    def tearDown(self):
        settings.KEYCLOAK_EXEMPT_URIS = []
        settings.KEYCLOAK_CONFIG['KEYCLOAK_SERVER_URL'] = 'https://localhost:8080/auth/'
    
    def test_when_has_not_some_keycloak_configuration_settings(self):
        
        # GIVEN doesn't configurated keycloak django settings
        del settings.KEYCLOAK_CONFIG['KEYCLOAK_SERVER_URL']

        # WHEN makes a request
        # THEN throws configuration exception
        with self.assertRaises(Exception):
            response = self.client.get(self.uri)
            KeycloakMiddleware(HttpResponse)(self.request)
    
    def test_when_some_URI_is_permitted_on_authentication_with_keycloak_roles_on_view(self):
        
        # GIVEN that a URL has been given that it will fire without authorization
        settings.KEYCLOAK_EXEMPT_URIS = ['core/banks']

        # WHEN makes a request that has 'keycloak_roles' attribute on View
        response = self.client.get(self.uri)

        # THEN allows endpoint to be accessed
        self.assertEquals(response.status_code, status.HTTP_200_OK)
    
    def test_when_some_URI_is_permitted_on_authentication_without_keycloak_roles_attribute_on_view(self):
        
        # GIVEN i've got a URI without 'keycloak_roles' on the View
        uri_no_roles = '/core/cars'

        # WHEN makes a request
        response = self.client.get(uri_no_roles)

        # THEN allows endpoint to be accessed
        self.assertEquals(response.status_code, status.HTTP_200_OK)
    
    def test_when_some_URI_without_authorization_on_http_header(self):

        # GIVEN a View endpoint
        view = views.BankViewSet.as_view({'get': 'list'})        
        
        # WHEN makes GET request without HTTP_AUTHORIZATIOND
        request = self.factory.get(self.uri)
        response = KeycloakMiddleware(Mock()).process_view(request, view, [], {})
                
        # THEN not allows endpoint to be accessed (401)
        self.assertEquals(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_when_token_not_active(self):
        # GIVEN token as not valid
        KeycloakConnect.is_token_active = Mock(return_value=False)

        # GIVEN a View endpoint
        view = views.BankViewSet.as_view({'get': 'list'})

        # GIVEN a fake request
        request = self.factory.get(self.uri)
        request.META['HTTP_AUTHORIZATION'] = 'Bearer token'
        
        # WHEN middleware is processed
        response = KeycloakMiddleware(Mock()).process_view(request, view, [], {})
                
        # THEN not allows endpoint to be accessed (401)
        self.assertEquals(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_when_token_as_active_and_no_roles_request_not_authorizated(self):
        # GIVEN token as valid
        KeycloakConnect.is_token_active = Mock(return_value=True)

        # GIVEN token has no roles
        KeycloakConnect.roles_from_token = Mock(return_value=None)

        # GIVEN a View endpoint
        view = views.BankViewSet.as_view({'get': 'list'})

        # GIVEN a fake request
        request = self.factory.get(self.uri)
        request.META['HTTP_AUTHORIZATION'] = 'Bearer token_fake'       
        
        # WHEN middleware is processed
        response = KeycloakMiddleware(Mock()).process_view(request, view, [], {})
                
        # THEN not allows endpoint to be accessed (401)
        self.assertEquals(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_when_token_as_active_and_has_roles_request_not_authorizated(self):
        # GIVEN token as valid
        KeycloakConnect.is_token_active = Mock(return_value=True)

        # GIVEN token has different role
        KeycloakConnect.roles_from_token = Mock(return_value=['xxxxxx'])

        # GIVEN a View endpoint has a 'diretor' role on GET method
        view = views.BankViewSet.as_view({'get': 'list'})
        view.keycloak_roles = {'GET': ['director']}

        # GIVEN a fake request
        request = self.factory.get(self.uri)
        request.META['HTTP_AUTHORIZATION'] = 'Bearer token_fake'       
        
        # WHEN middleware is processed
        response = KeycloakMiddleware(Mock()).process_view(request, view, [], {})
        
        # THEN does't allow endpoint authorization
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_when_token_as_active_and_has_roles_request_authorizated(self):
        # GIVEN token as valid
        KeycloakConnect.is_token_active = Mock(return_value=True)

        # GIVEN token has roles
        KeycloakConnect.roles_from_token = Mock(return_value=['director'])

        # GIVEN a View endpoint has a 'diretor' role on GET method
        view = views.BankViewSet.as_view({'get': 'list'})
        view.keycloak_roles = {'GET': ['director']}

        # GIVEN a fake request
        request = self.factory.get(self.uri)
        request.META['HTTP_AUTHORIZATION'] = 'Bearer token_fake'       
        
        # WHEN middleware is processed
        response = KeycloakMiddleware(Mock()).process_view(request, view, [], {})
        
        # THEN allows endpoint and pass token roles to request View
        self.assertEquals(['director'], request.roles)
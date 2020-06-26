Social logins
=============

To use Single Sign On (SSO) with Google, retrieve your key and secret
from Google and add them to the credentials file.

    .. code-block:: python

        SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = "[REDACTED]"
        SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = "[REDACTED]"


Then in the djaoapp/templates/accounts/login.html template file,
add the following HTML snipset:

    .. code-block:: html

        <a href="{{urls.user.login_google}}{% if next %}?next={{next}}{% endif %}">
          Login with Google
        </a>


Note: You cannot test this functionality through _localhost_. You will need
a valid domain name and server accessible through the Internet to test
everything is setup properly.

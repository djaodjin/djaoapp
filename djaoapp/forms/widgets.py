from django_recaptcha.widgets import ReCaptchaV2Checkbox


class CSPReCaptchaV2Checkbox(ReCaptchaV2Checkbox):

    template_name = "django_recaptcha/csp_widget_v2_checkbox.html"

    def __init__(self, csp_nonce=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.csp_nonce = csp_nonce

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['csp_nonce'] = str(self.csp_nonce) if self.csp_nonce else ''
        return context

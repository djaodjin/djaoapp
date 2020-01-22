# Copyright (c) 2020 DjaoDjin inc.
# see LICENSE

#pylint: disable=no-init

from django.contrib.auth import get_user_model
from rest_framework import serializers
from saas.api.serializers import (
    OrganizationDetailSerializer as OrganizationBaseSerializer,
    OrganizationWithEndsAtByPlanSerializer,
    WithSubscriptionSerializer)
from saas.api.serializers import RoleSerializer as BaseRoleSerializer
from saas.models import get_broker, Role, ChargeItem
from signup.serializers import (ActivitySerializer as UserActivitySerializer,
    UserSerializer)
from rules.api.serializers import AppSerializer as RulesAppSerializer


class OrganizationDetailSerializer(OrganizationBaseSerializer):

    pass


class ProfileSerializer(OrganizationDetailSerializer):

    activities = UserActivitySerializer(many=True, read_only=True)
    subscriptions = WithSubscriptionSerializer(
        source='subscription_set', many=True, read_only=True)

    class Meta(OrganizationDetailSerializer.Meta):
        fields = OrganizationDetailSerializer.Meta.fields + (
            'activities', 'subscriptions')


class RoleSerializer(BaseRoleSerializer):

    user = UserSerializer(read_only=True)


class SessionSerializer(serializers.ModelSerializer):

    last_visited = serializers.DateTimeField(required=False)
    username = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    site = serializers.SerializerMethodField()
    invoice_keys = serializers.SerializerMethodField()
    session_key = serializers.SerializerMethodField()
    access_key = serializers.SerializerMethodField()
    secret_key = serializers.SerializerMethodField()
    security_token = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ('username', 'roles', 'site', 'last_visited', 'invoice_keys',
            'session_key', 'access_key', 'secret_key', 'security_token')
        read_only_fields = ('username', 'roles', 'site', 'last_visited',
            'invoice_keys',
            'session_key', 'access_key', 'secret_key', 'security_token')

    @staticmethod
    def get_username(request):
        return request.user.username

    @staticmethod
    def get_roles(request):
        results = {}
        role_key = None
        organizations = []
        prev_role_key = None
        serializer = OrganizationWithEndsAtByPlanSerializer(many=True)
        for role in Role.objects.valid_for(user=request.user).order_by(
                'role_description').select_related('role_description'):
            role_key = role.role_description.slug
            if not prev_role_key:
                prev_role_key = role_key
            elif role_key != prev_role_key:
                results[prev_role_key] = serializer.to_representation(
                    organizations)
                prev_role_key = role_key
                organizations = []
            organizations += [role.organization]
        if organizations:
            results[prev_role_key] = serializer.to_representation(organizations)
        return results

    @staticmethod
    def get_site(obj): #pylint:disable=unused-argument
        broker = get_broker()
        return {'printable_name': broker.printable_name, 'email': broker.email}

    def get_invoice_keys(self, request):
        rule = self.context.get('rule', None)
        if rule and rule.rule_op >= 1: # XXX Authenticated
            return [result['invoice_key']
                for result in ChargeItem.objects.to_sync(request.user).values(
                    'invoice_key').distinct()]
        return []

    @staticmethod
    def get_session_key(request):
        if hasattr(request, 'session'):
            return request.session.session_key
        return None

    @staticmethod
    def get_access_key(request):
        if hasattr(request, 'session'):
            return request.session.get('access_key', None)
        return None

    @staticmethod
    def get_secret_key(request):
        if hasattr(request, 'session'):
            return request.session.get('secret_key', None)
        return None

    @staticmethod
    def get_security_token(request):
        if hasattr(request, 'session'):
            return request.session.get('security_token', None)
        return None


class AppSerializer(RulesAppSerializer):
    class Meta(RulesAppSerializer.Meta):
        fields = RulesAppSerializer.Meta.fields + ('show_edit_tools',)


class ActivitySerializer(serializers.Serializer):
    printable_name = serializers.CharField()
    descr = serializers.CharField()
    created_at = serializers.DateTimeField()
    slug = serializers.CharField()

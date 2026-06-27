from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.experiments.services import get_experiment_for_user

from .serializers import AlertRuleSerializer, AlertRuleUpdateSerializer, AlertRuleWriteSerializer
from .services import (
    create_alert_rule,
    delete_alert_rule,
    get_alert_rule_for_user,
    list_alert_rules,
    update_alert_rule,
)


class AlertRuleViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        rules = list_alert_rules(request.user)
        return Response(AlertRuleSerializer(rules, many=True).data)

    def create(self, request):
        serializer = AlertRuleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        experiment = get_experiment_for_user(data.pop('experiment'), request.user)
        rule = create_alert_rule(user=request.user, experiment=experiment, **data)
        return Response(AlertRuleSerializer(rule).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        rule = get_alert_rule_for_user(pk, request.user)
        return Response(AlertRuleSerializer(rule).data)

    def partial_update(self, request, pk=None):
        rule = get_alert_rule_for_user(pk, request.user)
        serializer = AlertRuleUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        rule = update_alert_rule(rule, **serializer.validated_data)
        return Response(AlertRuleSerializer(rule).data)

    def destroy(self, request, pk=None):
        rule = get_alert_rule_for_user(pk, request.user)
        delete_alert_rule(rule)
        return Response(status=status.HTTP_204_NO_CONTENT)

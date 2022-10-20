from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.utils import formats
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import GenericViewSet

from mysagw.caluma_client import CalumaClient
from mysagw.case import filters, models, serializers
from mysagw.case.permissions import HasCaseAccess
from mysagw.dms_client import DMSClient
from mysagw.identity.models import Address, Identity
from mysagw.oidc_auth.permissions import IsAdmin, IsAuthenticated

GQL_DIR = Path(__file__).parent.resolve() / "queries"


class CaseAccessViewSet(
    ListModelMixin,
    CreateModelMixin,
    DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = serializers.CaseAccessSerializer
    queryset = models.CaseAccess.objects.all()
    filterset_class = filters.CaseAccessFilterSet
    permission_classes = (IsAuthenticated & (IsAdmin | HasCaseAccess),)

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        if self.request.user.is_admin:
            return qs
        return qs.filter(
            case_id__in=qs.filter(identity=self.request.user.identity).values("case_id")
        )


class CaseDownloadViewSet(GenericViewSet):
    serializer_class = BaseSerializer
    permission_classes = (IsAuthenticated & (IsAdmin | HasCaseAccess),)

    ACKNOWLEDGEMENT_FIELDS = {
        "identity_submit": [
            "data",
            "node",
            "submit",
            "edges",
            0,
            "node",
            "closedByUser",
        ],
        "identity_revise": [
            "data",
            "node",
            "revise",
            "edges",
            0,
            "node",
            "closedByUser",
        ],
        "dossier_nr": [
            "data",
            "node",
            "main",
            "dossier_nr",
            "edges",
            0,
            "node",
            "value",
        ],
    }

    CREDIT_APPROVAL_FIELDS = {
        "identity_submit": [
            "data",
            "node",
            "submit",
            "edges",
            0,
            "node",
            "closedByUser",
        ],
        "identity_revise": [
            "data",
            "node",
            "revise",
            "edges",
            0,
            "node",
            "closedByUser",
        ],
        "dossier_nr": [
            "data",
            "node",
            "main",
            "dossier_nr",
            "edges",
            0,
            "node",
            "value",
        ],
        "rahmenkredit": [
            "data",
            "node",
            "decisionAndCredit",
            "edges",
            0,
            "node",
            "document",
            "credit",
            "edges",
            0,
            "node",
            "value",
        ],
    }

    @staticmethod
    def get_caluma_client(request):
        return CalumaClient(
            endpoint=f"{request.scheme}://{request.get_host()}/graphql",
            token=request.META.get("HTTP_AUTHORIZATION"),
            # For local testing:
            # endpoint="http://caluma:8000/graphql",
            # token="Bearer ey...",
        )

    def get_formatted_data(self, data, name):
        result = {}

        for field, path in getattr(self, f"{name.upper()}_FIELDS").items():
            value = None
            for node in path:
                if value is None:
                    value = data[node]
                    continue
                try:
                    value = value[node]
                except (KeyError, TypeError, IndexError):
                    value = ""
                    break

            result[field] = value

        # Identity has two possible sources
        identity_id = result["identity_submit"]
        if result["identity_revise"]:
            identity_id = result["identity_revise"]

        identity = Identity.objects.get(idp_id=identity_id)
        identity_dict = {
            "address_block": identity.address_block,
            "greeting_salutation_and_name": identity.greeting_salutation_and_name(),
            "language": identity.language,
        }

        result["identity"] = identity_dict
        del result["identity_submit"]
        del result["identity_revise"]

        result["date"] = formats.date_format(datetime.now())
        return result

    # @action(detail=True)
    # def application(self, request, pk=None):
    #     pass
    #     """
    #     name = "application"
    #     # prepare all answers for dms
    #     response = self.get_merged_document(data, name)
    #
    #     return response
    #     """

    def get_filename_translation(self, name, language):
        trans_map = {
            "acknowledgement": {
                "de": "Eingangsbestätigung",
                "en": "Acknowledgement of receipt",
                "fr": "Accusé de réception",
            },
            "credit_approval": {
                "de": "Kreditgutsprache",
                "en": "Credit approval",
                "fr": "Accord de crédit",
            },
        }
        return trans_map[name][language]

    def get_acknowledgement_and_credit_approval(self, request, name, pk=None):
        caluma_client = self.get_caluma_client(request)
        raw_data = caluma_client.get_data(pk, GQL_DIR / f"get_{name}.gql")
        try:
            data = self.get_formatted_data(raw_data, name)
        except (Identity.DoesNotExist, Address.DoesNotExist) as e:
            content = "Identity not found"
            if e.args[0].startswith("Address"):
                content = "No Address for identity"

            return HttpResponse(
                content,
                status=status.HTTP_400_BAD_REQUEST,
                content_type="text/plain",
            )

        dms_client = DMSClient()
        template = f'{getattr(settings, f"DOCUMENT_MERGE_SERVICE_{name.upper()}_TEMPLATE_SLUG")}-{data["identity"]["language"]}'
        status_code, content_type, content = dms_client.get_merged_document(
            data,
            template,
        )

        if status_code != status.HTTP_200_OK:
            return HttpResponse(content, status=status_code, content_type=content_type)

        file_name = (
            f"{data['dossier_nr']} - "
            f"{self.get_filename_translation(name, data['identity']['language'])}.pdf"
        )

        return FileResponse(
            content,
            filename=file_name,
        )

    @action(detail=True)
    def acknowledgement(self, request, pk=None):
        return self.get_acknowledgement_and_credit_approval(
            request, "acknowledgement", pk
        )

    @action(detail=True)
    def credit_approval(self, request, pk=None):
        return self.get_acknowledgement_and_credit_approval(
            request, "credit_approval", pk
        )

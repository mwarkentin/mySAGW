import io
from pathlib import Path

import requests
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from PyPDF2 import PdfMerger
from PyPDF2.errors import DependencyError, PdfReadError
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from rest_framework import status
from rest_framework.views import APIView

from mysagw.caluma_client import CalumaClient
from mysagw.dms_client import DMSClient
from mysagw.oidc_auth.permissions import IsAdmin, IsAuthenticated, IsStaff

GQL_DIR = Path(__file__).parent.resolve() / "queries"


def get_receipt_urls(data):
    try:
        rows = data["data"]["node"]["additionalData"]["edges"][0]["node"]["document"][
            "quittungen"
        ]["edges"][0]["node"]["value"]
    except (KeyError, TypeError, IndexError):
        return []

    result = []
    for row in rows:
        try:
            result += [
                url["downloadUrl"]
                for url in row["answers"]["edges"][0]["node"]["value"]
            ]
        except (KeyError, TypeError, IndexError):
            continue
    return result


def get_receipt(url):
    file = io.BytesIO()
    resp = requests.get(url, verify=False)
    file.write(resp.content)
    return {"file": file, "content-type": resp.headers.get("content-type")}


def get_cover_context(data):  # noqa: C901
    def mitgliedinstitution_label(slug):
        for option in data["data"]["node"]["main"]["mitgliedinstitution"]["edges"][0][
            "node"
        ]["question"]["options"]["edges"]:
            if option["node"]["slug"] == slug:
                return option["node"]["label"]

    def circ_kontonummer_label(slug):
        for option in data["data"]["node"]["decisionCredit"]["edges"][0]["node"][
            "document"
        ]["circKontonummer"]["edges"][0]["node"]["question"]["options"]["edges"]:
            if option["node"]["slug"] == slug:
                return option["node"]["label"]

    fields = {
        "form": (
            [
                "data",
                "node",
                "document",
                "form",
                "name",
            ],
            None,
        ),
        "applicant_address": (
            [
                "data",
                "node",
                "additionalData",
                "edges",
                0,
                "node",
                "document",
                "applicant_address",
                "edges",
                0,
                "node",
                "value",
            ],
            None,
        ),
        "applicant_postcode": (
            [
                "data",
                "node",
                "additionalData",
                "edges",
                0,
                "node",
                "document",
                "applicant_postcode",
                "edges",
                0,
                "node",
                "value",
            ],
            None,
        ),
        "applicant_city": (
            [
                "data",
                "node",
                "additionalData",
                "edges",
                0,
                "node",
                "document",
                "applicant_city",
                "edges",
                0,
                "node",
                "value",
            ],
            None,
        ),
        "applicant_land": (
            [
                "data",
                "node",
                "additionalData",
                "edges",
                0,
                "node",
                "document",
                "applicant_land",
                "edges",
                0,
                "node",
                "value",
            ],
            None,
        ),
        "applicant_name": (
            [
                "data",
                "node",
                "additionalData",
                "edges",
                0,
                "node",
                "document",
                "applicant_name",
                "edges",
                0,
                "node",
                "value",
            ],
            None,
        ),
        "bank": (
            [
                "data",
                "node",
                "additionalData",
                "edges",
                0,
                "node",
                "document",
                "bank",
                "edges",
                0,
                "node",
                "value",
            ],
            None,
        ),
        "bank_town": (
            [
                "data",
                "node",
                "additionalData",
                "edges",
                0,
                "node",
                "document",
                "bank_town",
                "edges",
                0,
                "node",
                "value",
            ],
            None,
        ),
        "dossier_no": (
            [
                "data",
                "node",
                "main",
                "dossierno",
                "edges",
                0,
                "node",
                "value",
            ],
            None,
        ),
        "fibu": (
            [
                "data",
                "node",
                "additionalData",
                "edges",
                0,
                "node",
                "document",
                "fibu",
                "edges",
                0,
                "node",
                "value",
            ],
            None,
        ),
        "zahlungszweck": (
            [
                "data",
                "node",
                "additionalData",
                "edges",
                0,
                "node",
                "document",
                "zahlungszweck",
                "edges",
                0,
                "node",
                "value",
            ],
            None,
        ),
        "iban": (
            [
                "data",
                "node",
                "additionalData",
                "edges",
                0,
                "node",
                "document",
                "iban",
                "edges",
                0,
                "node",
                "value",
            ],
            None,
        ),
        "section": (
            [
                "data",
                "node",
                "main",
                "sektion",
                "edges",
                0,
                "node",
                "value",
            ],
            lambda x: x.split("-")[1],
        ),
        "total": (
            [
                "data",
                "node",
                "defineAmount",
                "edges",
                0,
                "node",
                "document",
                "total",
                "edges",
                0,
                "node",
                "value",
            ],
            None,
        ),
        "vp_year": (
            [
                "data",
                "node",
                "main",
                "vp_year",
                "edges",
                0,
                "node",
                "value",
            ],
            lambda x: x.split("-")[3],
        ),
        "mitgliedinstitution": (
            [
                "data",
                "node",
                "main",
                "mitgliedinstitution",
                "edges",
                0,
                "node",
                "value",
            ],
            mitgliedinstitution_label,
        ),
        "circ_kontonummer": (
            [
                "data",
                "node",
                "decisionCredit",
                "edges",
                0,
                "node",
                "document",
                "circKontonummer",
                "edges",
                0,
                "node",
                "value",
            ],
            circ_kontonummer_label,
        ),
    }

    result = {}

    for field, path in fields.items():
        value = None
        for node in path[0]:
            if value is None:
                value = data[node]
                continue
            try:
                value = value[node]
            except (KeyError, TypeError, IndexError):
                value = ""
                break
        if value and path[1] is not None:
            value = path[1](value)
        result[field] = value

    return result


def get_files_to_merge(files):
    for file in files:
        if file["content-type"] == "application/pdf":
            yield file["file"]
        elif file["content-type"] in ["image/png", "image/jpeg"]:
            page = io.BytesIO()
            can = canvas.Canvas(page, pagesize=A4)
            image = ImageReader(file["file"])
            height = image.getSize()[1]
            x_start = 50
            y_start = 800 - height
            can.drawImage(
                image,
                x_start,
                y_start,
                preserveAspectRatio=True,
                mask="auto",
            )
            can.save()
            page.seek(0)
            yield page


class ReceiptView(APIView):
    permission_classes = (IsAuthenticated & (IsAdmin | IsStaff),)

    def get(self, request, pk, **kwargs):
        caluma_client = CalumaClient(
            endpoint=f"{request.scheme}://{request.get_host()}/graphql",
            token=request.META.get("HTTP_AUTHORIZATION"),
            # For local testing:
            # endpoint="http://caluma:8000/graphql",
            # token="Bearer ey...",
        )
        raw_data = caluma_client.get_data(pk, GQL_DIR / "get_receipts.gql")

        cover_context = get_cover_context(raw_data)
        cover_context["date"] = timezone.now().date().strftime("%d. %m. %Y")

        receipt_urls = get_receipt_urls(raw_data)
        dms_client = DMSClient()
        status_code, content_type, cover_content = dms_client.get_merged_document(
            cover_context,
            settings.DOCUMENT_MERGE_SERVICE_ACCOUNTING_COVER_TEMPLATE_SLUG,
        )

        if status_code != status.HTTP_200_OK:
            return HttpResponse(
                cover_content, status=status_code, content_type=content_type
            )

        files = [get_receipt(url) for url in receipt_urls]

        merger = PdfMerger()
        merger.append(cover_content)

        for file in get_files_to_merge(files):
            try:
                merger.append(file)
            except PdfReadError:  # pragma: no cover
                ## faulty pdf
                pass
            except DependencyError as e:
                # we don't support AES encrypted PDFs
                if (
                    not e.args
                    or not e.args[0] == "PyCryptodome is required for AES algorithm"
                ):  # pragma: no cover
                    raise

        result = io.BytesIO()

        merger.write(result)
        merger.close()

        result.seek(0)

        response = FileResponse(
            result,
            content_type="application/pdf",
            filename=f"{cover_context.get('dossier_no', 'receipts')}.pdf",
        )

        return response

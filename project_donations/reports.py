"""
PDF report generation for OYA Project Donations.
Uses ReportLab to match existing OYA styling.
"""
from io import BytesIO
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def _get_styles():
    """Build OYA-styled paragraph styles."""
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="OYA-Title",
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=12,
        textColor=colors.HexColor("#1a1a2e"),
        fontName="Helvetica-Bold"
    ))
    styles.add(ParagraphStyle(
        name="OYA-Subtitle",
        fontSize=12,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor("#666666")
    ))
    styles.add(ParagraphStyle(
        name="OYA-Header",
        fontSize=11,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=6,
        textColor=colors.HexColor("#1a1a2e"),
        fontName="Helvetica-Bold"
    ))
    styles.add(ParagraphStyle(
        name="OYA-Label",
        fontSize=9,
        leading=12,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#666666")
    ))
    styles.add(ParagraphStyle(
        name="OYA-Value",
        fontSize=10,
        leading=13,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#1a1a2e"),
        fontName="Helvetica-Bold"
    ))
    styles.add(ParagraphStyle(
        name="OYA-Footer",
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#999999")
    ))
    return styles


def _currency(amount):
    """Format amount as Nigerian Naira."""
    if amount is None:
        amount = Decimal("0")
    return f"₦{amount:,.2f}"


def _build_table(data, col_widths, styles):
    """Build a consistently styled data table."""
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8f9fa")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 8),
    ]))
    return table


def generate_project_fundraising_report(project):
    """PDF: Project Fundraising Summary Report."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
    styles = _get_styles()
    elements = []

    elements.append(Paragraph("OKPO YOUTHS ASSOCIATION", styles["OYA-Title"]))
    elements.append(Paragraph("Project Fundraising Report", styles["OYA-Subtitle"]))
    elements.append(Spacer(1, 0.2*inch))

    info_data = [
        [Paragraph("Project:", styles["OYA-Label"]), Paragraph(project.title, styles["OYA-Value"])],
        [Paragraph("Status:", styles["OYA-Label"]), Paragraph(project.get_status_display(), styles["OYA-Value"])],
        [Paragraph("Target Amount:", styles["OYA-Label"]), Paragraph(_currency(project.target_amount), styles["OYA-Value"])],
        [Paragraph("Amount Raised:", styles["OYA-Label"]), Paragraph(_currency(project.fundraising_amount_raised), styles["OYA-Value"])],
        [Paragraph("Remaining:", styles["OYA-Label"]), Paragraph(_currency(project.fundraising_remaining_amount), styles["OYA-Value"])],
        [Paragraph("Progress:", styles["OYA-Label"]), Paragraph(f"{project.fundraising_progress_percentage}%", styles["OYA-Value"])],
    ]
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))

    elements.append(Paragraph("Donation Records", styles["OYA-Header"]))
    elements.append(Spacer(1, 0.1*inch))

    from .models import Donation
    donations = Donation.objects.filter(
        project=project, status="CONFIRMED"
    ).select_related("member", "outside_donor", "recorded_by").order_by("-donation_date")

    if donations:
        table_data = [["Date", "Donor", "Type", "Amount", "Method", "Reference"]]
        for d in donations:
            donor_name = ""
            if d.member:
                donor_name = d.member.full_name
            elif d.outside_donor:
                donor_name = d.outside_donor.full_name
            else:
                donor_name = "Anonymous"
            table_data.append([
                d.donation_date.strftime("%Y-%m-%d"),
                donor_name,
                d.get_donor_type_display(),
                _currency(d.amount),
                d.get_payment_method_display(),
                d.reference_number or "-"
            ])
        elements.append(_build_table(table_data, [1*inch, 1.8*inch, 1*inch, 1.1*inch, 1.1*inch, 1.2*inch], styles))
    else:
        elements.append(Paragraph("No confirmed donations recorded.", styles["Normal"]))

    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(
        f"Report generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}",
        styles["OYA-Label"]
    ))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def generate_outside_donor_statement(donor):
    """PDF: Individual Outside Donor Statement."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
    styles = _get_styles()
    elements = []

    elements.append(Paragraph("OKPO YOUTHS ASSOCIATION", styles["OYA-Title"]))
    elements.append(Paragraph("Outside Donor Statement", styles["OYA-Subtitle"]))
    elements.append(Spacer(1, 0.2*inch))

    elements.append(Paragraph(f"Donor: <b>{donor.full_name}</b>", styles["OYA-Header"]))
    elements.append(Paragraph(f"Phone: {donor.phone_number or 'N/A'}", styles["OYA-Label"]))
    elements.append(Paragraph(f"Invited By: {donor.invited_by.full_name if donor.invited_by else 'N/A'}", styles["OYA-Label"]))
    elements.append(Paragraph(f"Total Donations: <b>{_currency(donor.total_donations)}</b>", styles["OYA-Header"]))
    elements.append(Spacer(1, 0.2*inch))

    from .models import Donation
    donations = Donation.objects.filter(
        outside_donor=donor, status="CONFIRMED"
    ).select_related("project").order_by("-donation_date")

    if donations:
        table_data = [["Date", "Project", "Amount", "Method", "Narration"]]
        for d in donations:
            table_data.append([
                d.donation_date.strftime("%Y-%m-%d"),
                d.project.title,
                _currency(d.amount),
                d.get_payment_method_display(),
                (d.narration or "-")[:40]
            ])
        elements.append(_build_table(table_data, [1*inch, 2*inch, 1.2*inch, 1.2*inch, 2*inch], styles))
    else:
        elements.append(Paragraph("No donation records found.", styles["Normal"]))

    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(
        f"Generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}",
        styles["OYA-Label"]
    ))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def generate_member_donation_history_report(member):
    """PDF: Member Donation History Report."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
    styles = _get_styles()
    elements = []

    elements.append(Paragraph("OKPO YOUTHS ASSOCIATION", styles["OYA-Title"]))
    elements.append(Paragraph("Member Donation History", styles["OYA-Subtitle"]))
    elements.append(Spacer(1, 0.2*inch))

    elements.append(Paragraph(f"Member: <b>{member.full_name}</b>", styles["OYA-Header"]))
    elements.append(Paragraph(f"Serial: {member.serial_number}", styles["OYA-Label"]))

    from .models import Donation
    donations = Donation.objects.filter(
        member=member, status="CONFIRMED"
    ).select_related("project").order_by("-donation_date")

    total = donations.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    elements.append(Paragraph(f"Total Donations: <b>{_currency(total)}</b>", styles["OYA-Header"]))
    elements.append(Spacer(1, 0.2*inch))

    if donations:
        table_data = [["Date", "Project", "Amount", "Method", "Narration"]]
        for d in donations:
            table_data.append([
                d.donation_date.strftime("%Y-%m-%d"),
                d.project.title,
                _currency(d.amount),
                d.get_payment_method_display(),
                (d.narration or "-")[:40]
            ])
        elements.append(_build_table(table_data, [1*inch, 2*inch, 1.2*inch, 1.2*inch, 2*inch], styles))
    else:
        elements.append(Paragraph("No donation records found.", styles["Normal"]))

    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(
        f"Generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}",
        styles["OYA-Label"]
    ))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def generate_donation_history_report(donations):
    """PDF: Complete Donation History Report (landscape)."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), topMargin=1*cm, bottomMargin=1*cm
    )
    styles = _get_styles()
    elements = []

    elements.append(Paragraph("OKPO YOUTHS ASSOCIATION", styles["OYA-Title"]))
    elements.append(Paragraph("Donation History Report", styles["OYA-Subtitle"]))
    elements.append(Spacer(1, 0.2*inch))

    if donations:
        table_data = [[
            "Date", "Project", "Donor", "Type", "Amount",
            "Method", "Recorded By", "Status"
        ]]
        for d in donations:
            donor_name = ""
            if d.member:
                donor_name = d.member.full_name
            elif d.outside_donor:
                donor_name = d.outside_donor.full_name
            else:
                donor_name = "Anonymous"

            table_data.append([
                d.donation_date.strftime("%Y-%m-%d"),
                d.project.title,
                donor_name,
                d.get_donor_type_display(),
                _currency(d.amount),
                d.get_payment_method_display(),
                d.recorded_by.get_full_name() if d.recorded_by else "-",
                d.get_status_display()
            ])
        elements.append(_build_table(
            table_data,
            [0.9*inch, 1.8*inch, 1.5*inch, 0.9*inch, 1*inch, 1*inch, 1.2*inch, 0.9*inch],
            styles
        ))
    else:
        elements.append(Paragraph("No donation records found.", styles["Normal"]))

    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(
        f"Generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}",
        styles["OYA-Label"]
    ))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

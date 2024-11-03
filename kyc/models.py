from django.db import models

from userservice.models import Users


class KYC(models.Model):
    user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name="kyc_info")
    document_type = models.CharField(
        max_length=50,
        choices=[
            ("passport", "Passport"),
            ("voter_card", "Voter's Card"),
            ("national_id", "National ID"),
            ("driver_license", "Driver's License"),
            ("residence_permit", "Residence Permit"),
            ("other", "Other"),
        ],
        null=True,
        blank=True,
    )
    kyc_document = models.ImageField(
        upload_to="business/kyc_document/",
        null=True,
        blank=True,
        verbose_name="kyc document",
        help_text="Upload a kyc document with a maximum size of 500x500 pixels",
    )
    document_issue_date = models.DateField(null=True, blank=True)
    document_expiry_date = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=50, null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
        ],
        null=True,
        blank=True,
    )
    occupation = models.CharField(max_length=100, null=True, blank=True)
    issuing_country = models.CharField(max_length=50, null=True, blank=True)

    # Address Information
    current_address = models.TextField(null=True, blank=True)  # business address instead

    # Additional KYC Documents
    proof_of_address = models.FileField(
        upload_to="business/business_address/", blank=True, null=True
    )

    # Additional Notes
    notes = models.TextField(blank=True, null=True)

    # Timestamps
    kyc_submission_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"KYC for {self.user.business_name}"

    class Meta:
        app_label = "kyc"

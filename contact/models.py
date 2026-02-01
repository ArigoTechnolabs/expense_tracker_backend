from django.db import models
from django.utils import timezone


class ContactSubmission(models.Model):
    """Model to store contact form submissions"""

    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact Submission"
        verbose_name_plural = "Contact Submissions"

    def __str__(self):
        return f"Contact from {self.name} ({self.email})"

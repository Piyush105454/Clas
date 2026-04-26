from django.db import models
import uuid


class Cluster(models.Model):
    """
    Cluster/Area model to group schools by geographic or administrative clusters
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=200, unique=True, help_text="Cluster/Area name")
    district = models.CharField(max_length=100, help_text="District this cluster belongs to")
    state = models.CharField(max_length=100, default="Madhya Pradesh", help_text="State/Province")
    
    description = models.TextField(blank=True, null=True, help_text="Description of the cluster")
    
    # Center coordinates for the cluster
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True,
        blank=True,
        help_text="Cluster center latitude"
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True,
        blank=True,
        help_text="Cluster center longitude"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["district", "name"]
        verbose_name = "Cluster"
        verbose_name_plural = "Clusters"
    
    def __str__(self):
        return f"{self.name} ({self.district})"

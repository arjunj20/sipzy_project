from django.db import models
from cloudinary.models import CloudinaryField
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    def __str__(self):
        return self.name


class Products(models.Model):
    
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class ProductVariants(models.Model):

    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name="variants")
    variant = models.CharField(max_length=100 )
    price = models.DecimalField(max_digits=10, decimal_places=2) 
    primary_image = CloudinaryField('image')
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.variant}"
class ProductImage(models.Model):
    variant = models.ForeignKey(ProductVariants, on_delete=models.CASCADE, related_name="images")
    image = CloudinaryField("image")
    created_at = models.DateTimeField(auto_now_add=True)



# Create your models here.

from django.db import models
from db_connection import db


# Create your models here.
Product = db['Product']
Supplier = db['Supplier']
Sale_order = db['Sale_order']
Stock_Movement = db['Stock_Movement']

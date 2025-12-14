from django.urls import path  
from .views import ClientSearchView  

urlpatterns = [  
    path('', ClientSearchView.as_view(), name='client-search'),  
]  
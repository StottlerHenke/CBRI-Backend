"""cbri URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from rest_framework_jwt.views import obtain_jwt_token
from rest_framework_jwt.views import refresh_jwt_token

from store.views import *

router = routers.DefaultRouter()
router.register(r'organizations', OrganizationViewSet)
router.register(r'users', InsightUserViewSet)
router.register(r'repositories', RepositoryViewSet)
router.register(r'repositories/(?P<repo>[^/.]+)/measurements', MeasurementViewSet, 'measurement')
router.register(r'repositories/(?P<repo>[^/.]+)/measurements/(?P<measurement>[^/.]+)/components', ComponentMeasurementViewSet, 'component')
router.register(r'repositories/(?P<repo>[^/.]+)/measurements/(?P<measurement>[^/.]+)/scores', MeasurementScoreViewSet, 'score')
router.register(r'repositories/(?P<repo>[^/.]+)/benchmarks', BenchmarkViewSet, 'benchmark')
router.register(r'repositories/(?P<repo>[^/.]+)/benchmark_descriptions', BenchmarkDescriptionViewSet, 'benchmark_description')

urlpatterns = [
    path('api/', include(router.urls)),
    url('api/cbri-settings', SettingsAPIView.as_view()),
    url('api/supported-languages', SupportedLanguagesAPIView.as_view()),
    url('api/login', obtain_jwt_token),
    url('api/current-user', CurrentUserView.as_view()),
    # Special path to create users without authentication -djc 2018-04-25
    url('api/create-user', CreateInsightUserView.as_view()),
    url('api/refresh-token', refresh_jwt_token)
]

# Disable admin URLs
if settings.ADMIN_ENABLED:
    urlpatterns.append(path('admin/', admin.site.urls))

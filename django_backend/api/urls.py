#路由系统，URL与视图绑定
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DataFileViewSet, CleanedDataViewSet, AnalysisResultViewSet, 
    VisualizationResultViewSet, RegisterView, CustomAuthToken, UserProfileView
)

router = DefaultRouter()
router.register(r'datafiles', DataFileViewSet)
router.register(r'cleaneddata', CleanedDataViewSet)
router.register(r'analysisresults', AnalysisResultViewSet)
router.register(r'visualizations', VisualizationResultViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomAuthToken.as_view(), name='login'),
    path('profile/', UserProfileView.as_view(), name='profile'),
] 
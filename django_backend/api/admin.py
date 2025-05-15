#自动生成的后台管理系统
from django.contrib import admin
from .models import DataFile, CleanedData, AnalysisResult, VisualizationResult

@admin.register(DataFile)
class DataFileAdmin(admin.ModelAdmin):
    list_display = ('name', 'file_type', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('file_type', 'created_at')

@admin.register(CleanedData)
class CleanedDataAdmin(admin.ModelAdmin):
    list_display = ('original_file', 'cleaning_method', 'created_at')
    list_filter = ('cleaning_method', 'created_at')

@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ('data_file', 'analysis_type', 'created_at')
    list_filter = ('analysis_type', 'created_at')

@admin.register(VisualizationResult)
class VisualizationResultAdmin(admin.ModelAdmin):
    list_display = ('data_file', 'chart_type', 'title', 'created_at')
    list_filter = ('chart_type', 'created_at')
    search_fields = ('title',)

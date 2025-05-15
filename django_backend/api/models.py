from django.db import models
from django.contrib.auth.models import User
import uuid
import os

def get_file_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads/', filename)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    organization = models.CharField(max_length=255, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.user.username
#定义数据文件模型
class DataFile(models.Model):
    #用户字段，存储上传文件的用户
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='datafiles', null=True)
    #文件字段，存储上传的文件
    file = models.FileField(upload_to=get_file_path)
    #文件名称，用于显示
    name = models.CharField(max_length=255)
    #描述，用于描述文件
    description = models.TextField(blank=True, null=True)
    #
    file_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
#定义清洗数据模型
class CleanedData(models.Model):
    original_file = models.ForeignKey(DataFile, on_delete=models.CASCADE, related_name='cleaned_data')
    file = models.FileField(upload_to='cleaned/')
    cleaning_method = models.CharField(max_length=50)
    parameters = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"清洗数据 - {self.original_file.name} - {self.cleaning_method}"

class AnalysisResult(models.Model):
    ANALYSIS_TYPES = (
        ('clustering', '聚类分析'),
        ('regression', '回归分析'),
        ('classification', '分类分析'),
        ('dimension_reduction', '降维分析'),
    )
    
    data_file = models.ForeignKey(DataFile, on_delete=models.CASCADE, related_name='analysis_results')
    cleaned_data = models.ForeignKey(CleanedData, on_delete=models.SET_NULL, null=True, blank=True, related_name='analysis_results')
    analysis_type = models.CharField(max_length=50, choices=ANALYSIS_TYPES)
    parameters = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_analysis_type_display()} - {self.data_file.name}"

class VisualizationResult(models.Model):
    CHART_TYPES = (
        ('line', '折线图'),
        ('bar', '柱状图'),
        ('scatter', '散点图'),
        ('pie', '饼图'),
        ('heatmap', '热力图'),
        ('box', '箱线图'),
        ('radar', '雷达图'),
    )
    
    analysis_result = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name='visualizations', null=True, blank=True)
    data_file = models.ForeignKey(DataFile, on_delete=models.CASCADE, related_name='visualizations')
    chart_type = models.CharField(max_length=50, choices=CHART_TYPES)
    title = models.CharField(max_length=255)
    configuration = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_chart_type_display()} - {self.title}"

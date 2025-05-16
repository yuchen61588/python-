from django.shortcuts import render
from rest_framework import viewsets, status, generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.views import APIView

import pandas as pd
import numpy as np
import os
import json
import traceback
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from .models import DataFile, CleanedData, AnalysisResult, VisualizationResult, UserProfile
from .serializers import (
    DataFileSerializer, CleanedDataSerializer, AnalysisResultSerializer, 
    VisualizationResultSerializer, UserSerializer, UserProfileSerializer, RegisterSerializer
)

class RegisterView(generics.CreateAPIView):
    # 用户注册
    # 得到所有用户数据
    queryset = User.objects.all()
    '''
    这段代码定义了 serializer_class 属性，用于指定视图中使用的序列化器类。
    在这里，RegisterSerializer 被用作序列化器类，负责处理用户注册时的数据验证和序列化。
    序列化器的作用是将复杂的 Python 数据类型（如模型实例）转换为 JSON 等可序列化格式，同时也可以验证输入数据的合法性。
    例如，在用户注册时，RegisterSerializer 会验证用户提交的数据是否符合要求（如用户名是否唯一、密码是否符合规则），并在验证通过后创建用户对象。
    通过将 serializer_class 设置为 RegisterSerializer，RegisterView 视图可以直接使用该序列化器来处理用户注册的请求数据，从而简化了视图的实现逻辑。
    '''
    serializer_class = RegisterSerializer
    # 允许所有用户访问注册接口
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request, *args, **kwargs):
        # 获取与视图关联的序列化器（RegisterSerializer），并将请求中的数据传递给它
        serializer = self.get_serializer(data=request.data)
        # 验证传入的数据是否合法。如果数据无效，会抛出异常并返回错误响应。
        serializer.is_valid(raise_exception=True)
        # 如果数据有效，调用序列化器的 save 方法来创建用户对象
        user = serializer.save()
        
        # 创建用户资料
        UserProfile.objects.create(user=user)
        
        # 创建token，使用 Django REST Framework 的 Token 模型为用户生成一个唯一的认证令牌（Token）。
        # 如果该用户已经有令牌，则返回现有令牌
        token, created = Token.objects.get_or_create(user=user)

        # 使用 UserSerializer 将用户对象序列化为 JSON 格式。
        # 返回包含用户数据和认证令牌的响应，供前端使用。
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key
        })

# 用于处理用户登录请求并返回用户的认证令牌和相关信息
class CustomAuthToken(ObtainAuthToken):
    # 用户登录
    def post(self, request, *args, **kwargs):
        # self.serializer_class 是 ObtainAuthToken 默认的序列化器类，用于验证用户提交的登录数据（如用户名和密码）
        serializer = self.serializer_class(data=request.data, context={'request': request})
        # 调用序列化器的 is_valid 方法来验证用户提交的数据是否合法
        serializer.is_valid(raise_exception=True)
        # 如果数据有效，获取用户对象
        user = serializer.validated_data['user']
        # 创建或获取与用户关联的认证令牌（Token）
        token, created = Token.objects.get_or_create(user=user)
        # 返回包含用户的认证令牌、用户 ID、用户名和电子邮件地址的 JSON 响应
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email
        })

# 用于获取和修改当前登录用户的个人资料
class UserProfileView(generics.RetrieveUpdateAPIView):
    # 指定了 UserProfileSerializer 作为序列化器类。
    # 序列化器负责将用户资料对象转换为 JSON 格式以供前端使用，同时验证和处理用户提交的更新数据。
    serializer_class = UserProfileSerializer
    # 仅允许已登录的用户访问该视图。
    # 未登录用户尝试访问时会返回 401 未授权错误。
    permission_classes = [permissions.IsAuthenticated]

    # 重写了 get_object 方法，用于返回当前登录用户的 UserProfile 对象。
    # self.request.user 是当前登录的用户对象，self.request.user.profile 是与该用户关联的用户资料。
    # 通过这种方式，确保用户只能访问和修改自己的资料，而不能操作其他用户的资料。
    def get_object(self):
        return self.request.user.profile

# 用于处理与数据文件相关的操作，包括上传、列出、删除文件以及预览 CSV 文件内容
class DataFileViewSet(viewsets.ModelViewSet):
    # queryset 属性定义了视图集的基本查询集，表示该视图集将处理所有 DataFile 对象。
    queryset = DataFile.objects.all()
    # serializer_class 属性指定了使用的序列化器类，用于将 DataFile 对象转换为 JSON 格式。
    serializer_class = DataFileSerializer

    # 该方法重写了默认的查询集逻辑。
    # 如果用户已登录，则返回当前用户上传的文件列表。
    # 如果用户未登录，则返回空查询集，确保未授权用户无法访问任何文件。
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return DataFile.objects.filter(user=self.request.user)
        return DataFile.objects.none()

    # 在保存文件时自动将当前登录用户设置为文件的拥有者。
    # 确保每个文件都与上传的用户关联。
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # 定义了一个自定义动作 preview，通过 @action 装饰器标记为支持 GET 请求的视图。
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        # data_file = self.get_object() 获取当前请求的文件对象。
        data_file = self.get_object()
        try:
            # 使用 pandas 读取文件路径中的 CSV 文件内容。
            df = pd.read_csv(data_file.file.path)
            
            # 确保布尔值被正确序列化
            df = df.replace({True: 'true', False: 'false'})
            
            # 确保数据类型兼容JSON序列化
            # 遍历 CSV 文件的每一行，将数据逐列处理：
            # 如果值是空值（NaN），设置为 None。
            # 如果值是整数类型，转换为 Python 的 int。
            # 如果值是浮点数类型，转换为 Python 的 float。
            # 其他类型直接保留原值。
            # 最终将每一行数据存储为字典，并添加到 data_dict 列表中。
            data_dict = []
            for _, row in df.iterrows():
                row_dict = {}
                for col in df.columns:
                    value = row[col]
                    if pd.isna(value):
                        row_dict[col] = None
                    elif isinstance(value, (np.int64, np.int32)):
                        row_dict[col] = int(value)
                    elif isinstance(value, (np.float64, np.float32)):
                        row_dict[col] = float(value)
                    else:
                        row_dict[col] = value
                data_dict.append(row_dict)

            # 返回一个包含以下信息的 JSON 响应：
            # columns：CSV 文件的列名列表。
            # data：处理后的文件内容，每一行是一个字典。
            # info：文件的元信息，包括数据形状（行数和列数）以及每列的数据类型。
            return Response({
                'columns': df.columns.tolist(),
                'data': data_dict,
                'info': {
                    'shape': [int(x) for x in df.shape],
                    'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()}
                }
            })
        # 捕获文件读取或处理过程中可能发生的异常。
        # 返回包含错误信息的响应，状态码为 400（错误请求）。
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# 用于处理与数据清洗相关的操作，包括获取清洗数据列表和执行数据清洗
class CleanedDataViewSet(viewsets.ModelViewSet):
    # 定义了视图集操作的默认查询集，这里是所有的 CleanedData 对象
    # CleanedData 是一个 Django 模型类，用于存储对原始数据文件进行清洗后的结果文件及相关信息。具体来说，它包含以下数据：
    # original_file: 关联的原始数据文件（DataFile 对象），表示清洗操作基于哪个原始文件。
    # file: 清洗后的文件存储路径，保存清洗后的数据文件。
    # cleaning_method: 使用的清洗方法名称（如“缺失值填充”、“去重”等）。
    # parameters: 清洗过程中使用的参数配置（以 JSON 格式存储）。
    # created_at: 清洗记录的创建时间。
    # 这些数据记录了清洗操作的详细信息，便于追踪和管理清洗后的数据文件。
    queryset = CleanedData.objects.all()
    # 指定了序列化器类 CleanedDataSerializer，用于将 CleanedData 模型实例转换为 JSON 格式，或将请求数据反序列化为模型实例。
    serializer_class = CleanedDataSerializer

    # 功能：重写了默认的查询集逻辑。
    # 如果用户已登录，则返回当前用户上传的文件关联的清洗数据。
    # 如果用户未登录，则返回空查询集，确保未授权用户无法访问任何清洗数据。
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return CleanedData.objects.filter(original_file__user=self.request.user)
        return CleanedData.objects.none()

    # 定义了一个自定义动作 clean_data，通过 @action 装饰器标记为支持 POST 请求的视图，用于执行数据清洗操作。
    @action(detail=False, methods=['post'])
    def clean_data(self, request):
        # file_id：要清洗的文件的 ID。
        # cleaning_method：清洗方法（如缺失值处理、离群值处理、标准化等）。
        # parameters：清洗方法的参数（如缺失值填充策略、离群值阈值等）。
        file_id = request.data.get('file_id')
        cleaning_method = request.data.get('cleaning_method')
        parameters = request.data.get('parameters', {})

        # 根据id得到要清洗的文件对象
        data_file = get_object_or_404(DataFile, id=file_id)
        # 功能：检查当前用户是否有权限访问指定的文件。
        # 如果文件的拥有者不是当前用户，且用户不是管理员，则返回 403 错误。
        # 检查用户是否有权限访问此文件
        if data_file.user != request.user and not request.user.is_staff:
            return Response({'error': '没有权限访问此文件'}, status=status.HTTP_403_FORBIDDEN)


        try:
            # 使用 pandas 读取文件路径中的数据文件（假设是 CSV 格式）。
            df = pd.read_csv(data_file.file.path)
            # 缺失值处理
            # mean：用列的均值填充缺失值。
            # median：用列的中位数填充缺失值。
            # mode：用列的众数填充缺失值。
            # drop：删除包含缺失值的行。
            if cleaning_method == 'missing_values':
                strategy = parameters.get('strategy', 'mean')
                if strategy == 'mean':
                    df = df.fillna(df.mean())
                elif strategy == 'median':
                    df = df.fillna(df.median())
                elif strategy == 'mode':
                    df = df.fillna(df.mode().iloc[0])
                elif strategy == 'drop':
                    df = df.dropna()
            # 离群值处理
            # 功能：使用 Z-Score 方法标记离群值，将其设为 NaN，然后用均值填充。
            # threshold：离群值的阈值（默认 3.0）。
            # numeric_cols：仅对数值列进行处理。
            elif cleaning_method == 'outliers':
                # 使用 z-score 方法标记离群值，将其设为 NaN，然后用均值填充。
                method = parameters.get('method', 'zscore')
                threshold = float(parameters.get('threshold', 3.0))
                
                if method == 'zscore':
                    numeric_cols = df.select_dtypes(include=[np.number]).columns
                    for col in numeric_cols:
                        df[col] = df[col].mask(np.abs((df[col] - df[col].mean()) / df[col].std()) > threshold, np.nan)
                    df = df.fillna(df.mean())
            # 标准化处理
            # 功能：对数值列进行标准化处理，使其均值为 0，标准差为 1。
            elif cleaning_method == 'standardization':
                scaler = StandardScaler()
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                df[numeric_cols] = scaler.fit_transform(df[numeric_cols])

            # 使用 f-string 格式化字符串，生成清洗后的文件名。
            # data_file.name 是原始文件的名称，cleaned_ 是前缀，用于标识这是清洗后的文件。
            # 例如，如果原始文件名是 data.csv，生成的 output_path 将是 cleaned_data.csv。
            output_path = f'cleaned_{data_file.name}'
            # 使用 os.path.join 将目录路径 'media/cleaned' 和文件名 output_path 拼接成完整的文件路径。
            # media/cleaned 是存储清洗后文件的目录，output_path 是文件名。
            # 例如，最终路径可能是 media/cleaned/cleaned_data.csv。
            output_file_path = os.path.join('media/cleaned', output_path)
            # 使用 os.makedirs 创建文件路径中包含的目录。
            # os.path.dirname(output_file_path) 获取文件路径的目录部分（如 media/cleaned）。
            # 参数 exist_ok=True 表示如果目录已存在，不会抛出异常。
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
            # 使用 pandas 的 to_csv 方法将数据框 df 保存为 CSV 文件。
            # output_file_path 是保存文件的完整路径。
            # 参数 index=False 表示不将数据框的索引写入 CSV 文件中
            df.to_csv(output_file_path, index=False)

            # 功能：在数据库中创建一条 CleanedData 记录，保存清洗后的文件路径、清洗方法和参数
            cleaned_data = CleanedData.objects.create(
                original_file=data_file,
                file=f'cleaned/{output_path}',
                cleaning_method=cleaning_method,
                parameters=parameters
            )
            # 将保存后的清洗结果通过序列化返回前端。
            serializer = self.get_serializer(cleaned_data)
            return Response(serializer.data)

        # 捕获清洗过程中可能发生的异常，并返回错误信息。
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
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

class AnalysisResultViewSet(viewsets.ModelViewSet):
    '''AnalysisResultViewSet，用于处理与数据分析相关的 API 请求。它继承自 ModelViewSet，
    自动提供了对数据库模型 AnalysisResult 的 CRUD 操作（创建、读取、更新、删除），并通
    过一个自定义的 analyze 动作方法实现了数据分析的核心功能。'''
    queryset = AnalysisResult.objects.all()  # 定义该视图集操作的数据源为所有 AnalysisResult 实例
    serializer_class = AnalysisResultSerializer  # 进行数据的序列化与反序列化，便于前后端交互。

    
    def get_queryset(self):
        '''
        如果用户已认证，则返回属于该用户的数据文件所关联的所有分析结果。
    否则返回空查询集，防止未授权访问。
        '''
        if self.request.user.is_authenticated:
            return AnalysisResult.objects.filter(data_file__user=self.request.user)
        return AnalysisResult.objects.none()


    #最核心的功能入口，允许客户端发起一个 POST 请求来进行以下类型的分析
    @action(detail=False, methods=['post'])#定义一个POST方法的自定义操作。detail=False表示该操作是针对集合的，而不是单个资源
    def analyze(self, request):
        # 打印请求数据，以便调试，检查客户端传递给服务器的数据
        print("接收到分析请求：", request.data)

        # 从请求中获取用户指定的原始数据文件的 ID。从请求数据中获取文件ID，用于后续处理中标识特定的文件
        file_id = request.data.get('file_id')

        # 从请求数据中获取清洗后的数据ID，用于关联或标识经过预处理的数据
        cleaned_data_id = request.data.get('cleaned_data_id')

        # 从请求数据中获取分析类型，决定后续数据处理或分析的具体方法
        analysis_type = request.data.get('analysis_type')

        # 从请求数据中获取额外的参数，这些参数是可选的，如果不存在则默认为空字典
        # 这些参数用于定制化分析过程中的特定行为或配置
        parameters = request.data.get('parameters', {})
        
        print(f"分析参数: file_id={file_id}, analysis_type={analysis_type}, parameters={parameters}")

        #检查是否提供了必要的参数
        if not file_id:
            # 创建一个 HTTP 响应对象，返回给客户端，专门用于处理结构化数据（如 JSON）
            # 如果缺少必要参数，则返回错误信息，并使用HTTP状态码400表示错误
            return Response({'error': '缺少必要参数：file_id'}, status=status.HTTP_400_BAD_REQUEST)
            
        if not analysis_type:
            return Response({'error': '缺少必要参数：analysis_type'}, status=status.HTTP_400_BAD_REQUEST)

        #根据file_id获取数据文件对象
        try:
            #数据库中获取一个对象，如果找不到该对象，则自动引发 Http404 异常。从 DataFile 表中查找 id 字段等于 file_id 的记录。
            data_file = get_object_or_404(DataFile, id=file_id)
            print(f"找到数据文件: {data_file.name}")
        except Exception as e:
            return Response({'error': f'无法找到ID为{file_id}的文件: {str(e)}'}, status=status.HTTP_404_NOT_FOUND)
        
        # 检查用户是否有权限访问此文件（文件的拥有者request.user，管理员request.user.is_staff
        if data_file.user != request.user and not request.user.is_staff:
            return Response({'error': '没有权限访问此文件'}, status=status.HTTP_403_FORBIDDEN)
        
        # 如果提供了cleaned_data_id，则使用清洗后的数据。没有则使用原始数据文件，确定使用哪个数据源
        if cleaned_data_id:
            try:
                cleaned_data = get_object_or_404(CleanedData, id=cleaned_data_id)
                file_path = cleaned_data.file.path
                print(f"使用清洗后的数据: {cleaned_data.file.name}")
            except Exception as e:
                return Response({'error': f'无法找到ID为{cleaned_data_id}的清洗数据: {str(e)}'}, status=status.HTTP_404_NOT_FOUND)
        else:
            file_path = data_file.file.path
            cleaned_data = None
            print(f"使用原始数据文件: {data_file.file.name}")

        try:
            print(f"尝试读取CSV文件: {file_path}")
            df = pd.read_csv(file_path)
            #打印读取成功后的数据维度（行数、列数）和前5个列名
            print(f"CSV读取成功，数据形状: {df.shape}, 列名: {df.columns.tolist()[:5]}...")
            result = {}
            
            # 验证请求中的特征是否存在于数据集中
            #从请求参数中获取用户指定的特征列表 features，默认为空列表
            requested_features = parameters.get('features', [])
            print(f"请求的特征: {requested_features}")
            #获取数据集 df 中所有可用的列名，转换为列表形式保存在
            available_columns = df.columns.tolist()
            
            # 过滤出实际存在于数据集的特征
            valid_features = [f for f in requested_features if f in available_columns]
            print(f"有效特征: {valid_features}")
            
            if not valid_features:
                # 如果没有有效特征，使用多种方法尝试检测数值型列
                print("没有有效特征，尝试多种方法检测数值列...")
                numeric_cols = []
                
                # 方法0: 处理BBQ_weather列
                #筛选出列名包含BBQ_weather的所有列
                bbq_cols = [col for col in df.columns if 'BBQ_weather' in col]
                if bbq_cols:
                    print(f"检测到BBQ_weather列: {bbq_cols}")
                    # 创建BBQ列的数值版本
                    for col in bbq_cols:
                        # 将BBQ值转换为0或1
                        col_name = f"{col}_numeric"
                        df[col_name] = df[col].map(lambda x: 1 if str(x).lower() in ['1', 'true', 't', 'yes', 'y', 'good'] else 0)
                        numeric_cols.append(col_name)
                    print(f"创建的BBQ数值列: {numeric_cols}")
                
                # 方法1: 使用pandas的数值类型检测
                try:
                    #选择所有数据类型为数值型的列
                    numeric_cols_pd = df.select_dtypes(include=[np.number]).columns.tolist()
                    print(f"方法1-Pandas检测到的数值列: {numeric_cols_pd}")
                    if numeric_cols_pd:
                        for col in numeric_cols_pd:
                            if col != 'DATE' and col not in numeric_cols:
                                numeric_cols.append(col)
                except Exception as e:
                    print(f"pandas数值列检测失败: {str(e)}")
                
                # 方法2: 尝试手动检测数值型列（分析每列前100行数据）
                if len(numeric_cols) < 3:
                    print("方法2-尝试手动检测数值列...")
                    for col in df.columns:
                        # 跳过DATE、MONTH和已处理的BBQ列
                        if col in ['DATE', 'MONTH'] or col in numeric_cols:
                            continue
                            
                        # 检查前100行样本确认是否为数值
                        sample = df[col].head(100).dropna()
                        if len(sample) == 0:
                            continue
                            
                        is_numeric = True
                        for val in sample:
                            try:
                                if val is None or pd.isna(val) or val == '':
                                    continue
                                float(val)
                            except (ValueError, TypeError):
                                is_numeric = False
                                break
                                
                        if is_numeric:
                            numeric_cols.append(col)
                    
                    print(f"方法2-手动检测到的数值列: {numeric_cols}")
                
                # 方法3: 转换DATE列为数值特征
                if len(numeric_cols) < 3 and 'DATE' in df.columns:
                    print("方法3-转换DATE列为数值特征...")
                    try:
                        # 从DATE列提取月份和日期作为数值特征
                        df['MONTH_numeric'] = pd.to_datetime(df['DATE']).dt.month
                        df['DAY_numeric'] = pd.to_datetime(df['DATE']).dt.day
                        numeric_cols.append('MONTH_numeric')
                        numeric_cols.append('DAY_numeric')
                        print(f"添加的时间数值特征: MONTH_numeric, DAY_numeric")
                    except Exception as e:
                        print(f"转换DATE列失败: {str(e)}")
                
                # 方法4: 最后尝试创建随机特征演示
                if len(numeric_cols) < 3:
                    print("方法4-创建随机特征来演示分析...")
                    for i in range(3):
                        col_name = f"random_feature_{i+1}"
                        df[col_name] = np.random.rand(len(df))
                        numeric_cols.append(col_name)
                    print(f"创建的随机特征: {numeric_cols[-3:]}")
                
                # 排除DATE和MONTH列
                valid_features = [f for f in numeric_cols if f not in ['DATE', 'MONTH']]
                
                print(f"最终选择的有效特征: {valid_features}")
                
                # 如果仍然没有有效特征，返回错误
                if not valid_features:
                    return Response({
                        'error': '没有可用的数值特征进行分析，请检查数据格式'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # 限制使用的默认特征数量
                if len(valid_features) > 5:
                    valid_features = valid_features[:5]
                    print(f"限制为前5个特征: {valid_features}")
                
            # 验证目标变量是否存在（对于回归和分类）
            target = parameters.get('target')
            if target:
                print(f"目标特征: {target}, 是否存在: {target in available_columns}")

            # 如果目标变量不存在于可用列中，尝试查找替代的目标变量
            if target and target not in available_columns:
                # 排除特定列，寻找潜在的目标变量
                potential_targets = [col for col in df.columns
                                   if col not in ['DATE', 'MONTH']
                                   and not col.endswith('BBQ_weather')
                                   and col not in valid_features]

                # 如果找到潜在的目标变量，选择第一个作为新的目标变量
                if potential_targets:
                    new_target = potential_targets[0]
                    print(f"目标特征 {target} 不存在，使用 {new_target} 作为替代")
                    target = new_target
                else:
                    # 如果没有找到替代目标变量，返回错误响应
                    return Response({
                        'error': f'目标特征 "{target}" 不存在于数据集中，且无法找到替代目标。可用列：{available_columns[:10]}...'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # 确保在继续之前valid_features不为空
            if not valid_features:
                return Response({
                    'error': '没有有效的特征可用于分析，请检查数据格式和列名'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            print(f"最终使用的特征: {valid_features}")
            print(f"数据样本:\n{df[valid_features].head()}")
            
            # 最终检查特征数据是否实际包含数值
            try:
                X = df[valid_features].astype(float)
                print(f"特征转换为数值成功，数据形状: {X.shape}")
                
                # 检查是否存在无限值或NaN
                if X.isnull().values.any() or np.isinf(X.values).any():
                    print("警告：数据中存在NaN或无限值，将进行填充")
                    X = X.fillna(X.mean())
                    X = X.replace([np.inf, -np.inf], X.mean())
            except Exception as e:
                print(f"转换特征为数值时出错: {str(e)}")
                return Response({
                    'error': f'转换特征为数值失败: {str(e)}。请确保选择的列只包含数值数据。'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 对不同的分析类型执行不同的操作
            if analysis_type == 'clustering':
                # 从参数中获取聚类数量，默认为3
                n_clusters = int(parameters.get('n_clusters', 3))
                # 打印聚类分析的执行信息
                print(f"执行聚类分析，聚类数: {n_clusters}, 特征数: {len(valid_features)}")

                try:
                    # 将有效特征转换为浮点类型
                    X = df[valid_features].astype(float)

                    # 初始化KMeans对象并进行聚类分析
                    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
                    clusters = kmeans.fit_predict(X)

                    # 构建聚类分析结果字典
                    result = {
                        'clusters': clusters.tolist(),
                        'centers': kmeans.cluster_centers_.tolist(),
                        'clusterCounts': [sum(clusters == i) for i in range(n_clusters)],
                        'feature_names': valid_features
                    }
                    # 打印聚类分析完成信息
                    print("聚类分析完成")
                except Exception as e:
                    # 打印并返回聚类分析失败的错误信息
                    print(f"聚类分析失败: {str(e)}")
                    return Response({'error': f'聚类分析失败: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

            elif analysis_type == 'dimension_reduction':
                # 从参数中获取降维后的组件数量，默认为2
                n_components = int(parameters.get('n_components', 2))
                # 打印降维分析的执行信息
                print(f"执行降维分析，组件数: {n_components}, 特征数: {len(valid_features)}")

                try:
                    # 将有效特征转换为浮点类型
                    X = df[valid_features].astype(float)

                    # 初始化PCA对象并进行降维分析
                    pca = PCA(n_components=n_components)
                    components = pca.fit_transform(X)

                    # 构建降维分析结果字典
                    result = {
                        'components': components.tolist(),
                        'explained_variance_ratio': pca.explained_variance_ratio_.tolist(),
                        'feature_names': valid_features
                    }
                    # 打印降维分析完成信息
                    print("降维分析完成")
                except Exception as e:
                    # 打印并返回降维分析失败的错误信息
                    print(f"降维分析失败: {str(e)}")
                    return Response({'error': f'降维分析失败: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)


            elif analysis_type == 'regression' and target:
                # 当分析类型为回归分析且目标变量已指定时，执行以下代码块
                print(f"执行回归分析，目标: {target}, 特征数: {len(valid_features)}")

                try:
                    # 将有效特征和目标变量转换为浮点类型
                    X = df[valid_features].astype(float)
                    y = df[target].astype(float)

                    # 使用更可靠的特征选择 - 计算与目标的相关性
                    correlations = []
                    for feature in valid_features:
                        corr = np.corrcoef(X[feature], y)[0, 1]
                        correlations.append((feature, abs(corr)))

                    # 按相关性排序特征
                    sorted_features = [f for f, _ in sorted(correlations, key=lambda x: x[1], reverse=True)]
                    print(f"特征按相关性排序: {sorted_features}")

                    # 使用相关性最高的特征
                    if len(sorted_features) > 5:
                        best_features = sorted_features[:5]
                        X = X[best_features]
                        print(f"使用相关性最高的5个特征: {best_features}")

                    # 分割训练集和测试集
                    test_size = float(parameters.get('test_size', 0.2))
                    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

                    # 根据算法选择模型
                    algorithm = parameters.get('algorithm', 'linear')
                    result = {}  # 初始化结果字典

                    # 如果选择的算法是随机森林
                    if algorithm == 'random_forest':
                        from sklearn.ensemble import RandomForestRegressor
                        # 创建随机森林回归器实例
                        model = RandomForestRegressor(n_estimators=100, random_state=42)
                        # 训练模型
                        model.fit(X_train, y_train)
                        # 使用训练好的模型进行预测
                        y_pred = model.predict(X_test)

                        # 获取特征重要性
                        feature_importance = model.feature_importances_.tolist()
                        intercept = 0.0  # 随机森林没有截距
                        extra_info = {'scaled': False}

                        print(f"随机森林回归分析完成")
                        
                    else:  # 线性回归相关算法
                        # 应用特征缩放，对线性模型很重要
                        from sklearn.preprocessing import StandardScaler
                        scaler = StandardScaler()
                        X_train_scaled = scaler.fit_transform(X_train)
                        X_test_scaled = scaler.transform(X_test)
                        
                        # 检查是否应用多项式特征
                        use_poly = parameters.get('use_polynomial', False)
                        poly_degree = int(parameters.get('polynomial_degree', 2))
                        
                        if use_poly:
                            from sklearn.preprocessing import PolynomialFeatures
                            poly = PolynomialFeatures(degree=poly_degree, include_bias=False)
                            X_train_scaled = poly.fit_transform(X_train_scaled)
                            X_test_scaled = poly.transform(X_test_scaled)
                            print(f"应用多项式特征，阶数: {poly_degree}")
                        
                        # 选择适当的线性回归变体
                        linear_type = parameters.get('linear_type', 'standard')
                        
                        if linear_type == 'ridge':
                            from sklearn.linear_model import Ridge
                            alpha = float(parameters.get('alpha', 1.0))
                            model = Ridge(alpha=alpha)
                            print(f"使用岭回归，alpha={alpha}")
                        elif linear_type == 'lasso':
                            from sklearn.linear_model import Lasso
                            alpha = float(parameters.get('alpha', 0.1))
                            model = Lasso(alpha=alpha)
                            print(f"使用Lasso回归，alpha={alpha}")
                        else:
                            # 标准线性回归
                            model = LinearRegression()
                            print("使用标准线性回归")
                        
                        # 使用缩放后的数据
                        model.fit(X_train_scaled, y_train)
                        y_pred = model.predict(X_test_scaled)
                        
                        # 获取系数和截距
                        if hasattr(model, 'coef_'):
                            if len(model.coef_.shape) == 1:
                                feature_importance = model.coef_.tolist()
                            else:
                                feature_importance = model.coef_[0].tolist()
                        else:
                            feature_importance = [0] * len(X.columns)
                            
                        intercept = float(model.intercept_) if hasattr(model, 'intercept_') else 0.0
                        
                        # 额外信息
                        extra_info = {
                            'scaled': True,
                            'linear_type': linear_type
                        }
                        if use_poly:
                            extra_info['polynomial'] = {
                                'applied': True,
                                'degree': poly_degree
                            }
                        
                        print(f"线性回归分析完成")
                    
                    # 计算通用的评估指标
                    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
                    r2 = r2_score(y_test, y_pred)
                    mae = mean_absolute_error(y_test, y_pred)
                    mse = mean_squared_error(y_test, y_pred)
                    
                    # 为了前端可视化，生成预测值与实际值比较
                    predictions = []
                    for i in range(min(20, len(X_test))):
                        actual = float(y_test.iloc[i]) if hasattr(y_test, 'iloc') else float(y_test[i])
                        predicted = float(y_pred[i])
                        predictions.append({'actual': actual, 'predicted': predicted})
                    
                    # 完成结果字典
                    result = {
                        'coefficients': feature_importance,
                        'intercept': intercept,
                        'feature_names': X.columns.tolist(),
                        'target': target,
                        'predictions': predictions,
                        'metrics': {
                            'r2': float(r2),
                            'mae': float(mae),
                            'mse': float(mse)
                        },
                        'algorithm': algorithm,
                        'extra_info': extra_info
                    }
                    
                    print(f"分析指标 - R²: {r2:.4f}, MAE: {mae:.4f}, MSE: {mse:.4f}")
                    
                    # 创建分析结果
                    analysis_result = AnalysisResult.objects.create(
                        data_file=data_file,
                        cleaned_data=cleaned_data,
                        analysis_type=analysis_type,
                        parameters={
                            **parameters,
                            'actual_features_used': valid_features  # 记录实际使用的特征
                        },
                        result=result
                    )
                    print(f"分析结果已保存，ID: {analysis_result.id}")
                    
                    serializer = self.get_serializer(analysis_result)
                    return Response(serializer.data)
                    
                except Exception as e:
                    print(f"回归分析失败: {str(e)}")
                    traceback.print_exc()  # 打印完整堆栈跟踪
                    return Response({'error': f'回归分析失败: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
                
            elif analysis_type == 'classification' and target:
                print(f"执行分类分析，目标: {target}, 特征数: {len(valid_features)}")
                
                try:
                    X = df[valid_features].astype(float)
                    y = df[target]
                    
                    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                    
                    model = RandomForestClassifier(random_state=42)
                    model.fit(X_train, y_train)
                    
                    result = {
                        'accuracy': float(model.score(X_test, y_test)),
                        'feature_importance': model.feature_importances_.tolist(),
                        'feature_names': valid_features
                    }
                    print("分类分析完成，准确率: ", result['accuracy'])
                except Exception as e:
                    print(f"分类分析失败: {str(e)}")
                    return Response({'error': f'分类分析失败: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'error': f'不支持的分析类型: {analysis_type}，或缺少必要参数'
                }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            import traceback
            print("分析过程中出现错误:")
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class VisualizationResultViewSet(viewsets.ModelViewSet):
    """
    VisualizationResult模型的视图集，提供CRUD功能
    """
    queryset = VisualizationResult.objects.all()
    serializer_class = VisualizationResultSerializer

    def get_queryset(self):
        """
        重写get_queryset方法，根据用户认证状态返回不同的查询集
        """
        # 如果用户已认证，则返回属于该用户的数据文件的可视化结果
        if self.request.user.is_authenticated:
            return VisualizationResult.objects.filter(data_file__user=self.request.user)
        # 如果用户未认证，则返回空查询集
        return VisualizationResult.objects.none()

    @action(detail=False, methods=['post'])
    def visualize(self, request):
        """
        处理可视化请求的自定义动作
        """
        # 从请求数据中获取参数
        data_file_id = request.data.get('data_file_id')
        analysis_result_id = request.data.get('analysis_result_id')
        chart_type = request.data.get('chart_type')
        title = request.data.get('title')
        configuration = request.data.get('configuration', {})

        # 获取数据文件对象
        data_file = get_object_or_404(DataFile, id=data_file_id)

        # 检查用户是否有权限访问此文件
        if data_file.user != request.user and not request.user.is_staff:
            return Response({'error': '没有权限访问此文件'}, status=status.HTTP_403_FORBIDDEN)

        # 获取分析结果对象，如果提供了分析结果ID
        analysis_result = None
        if analysis_result_id:
            analysis_result = get_object_or_404(AnalysisResult, id=analysis_result_id)

        # 创建可视化结果
        visualization = VisualizationResult.objects.create(
            data_file=data_file,
            analysis_result=analysis_result,
            chart_type=chart_type,
            title=title,
            configuration=configuration
        )

        # 使用序列化器序列化新创建的可视化结果并返回响应
        serializer = self.get_serializer(visualization)
        return Response(serializer.data)

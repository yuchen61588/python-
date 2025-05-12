import axios from "axios";

const baseURL = "http://localhost:8000/api";

const api = axios.create({
  baseURL,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// 请求拦截器 - 添加认证Token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers["Authorization"] = `Token ${token}`;
    }
    console.log("请求配置:", config);
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器 - 打印响应信息
api.interceptors.response.use(
  (response) => {
    console.log("API响应:", response);
    return response;
  },
  (error) => {
    console.error("API错误:", error.response || error.message || error);
    return Promise.reject(error);
  }
);

// 用户相关API
export const register = async (userData) => {
  console.log("注册请求数据:", userData);
  try {
    const response = await api.post("/register/", userData);
    console.log("注册成功:", response.data);
    return response;
  } catch (error) {
    console.error("注册失败:", error.response?.data || error.message);
    throw error;
  }
};

export const login = async (credentials) => {
  console.log("登录请求数据:", credentials);
  return api.post("/login/", credentials);
};

export const getUserProfile = async () => {
  return api.get("/profile/");
};

// 数据文件相关API
export const uploadFile = async (file, name, description) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", name || file.name);
  formData.append("description", description || "");
  formData.append("file_type", file.type);

  return api.post("/datafiles/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

export const getDataFiles = async () => {
  return api.get("/datafiles/");
};

export const getDataFilePreview = async (fileId) => {
  return api.get(`/datafiles/${fileId}/preview/`);
};

// 数据清洗相关API
export const cleanData = async (fileId, cleaningMethod, parameters) => {
  return api.post("/cleaneddata/clean_data/", {
    file_id: fileId,
    cleaning_method: cleaningMethod,
    parameters,
  });
};

export const getCleanedDataList = async () => {
  return api.get("/cleaneddata/");
};

// 数据分析相关API
export const runAnalysis = async (
  fileId,
  cleanedDataId,
  analysisType,
  parameters
) => {
  const requestData = {
    file_id: fileId,
    cleaned_data_id: cleanedDataId,
    analysis_type: analysisType,
    parameters,
  };

  console.log("发送数据分析请求:", JSON.stringify(requestData));

  try {
    const response = await api.post("/analysisresults/analyze/", requestData);
    console.log("分析结果:", response.data);
    return response;
  } catch (error) {
    console.error(
      "分析请求错误:",
      error.response
        ? {
            status: error.response.status,
            data: error.response.data,
          }
        : error.message
    );
    throw error;
  }
};

export const getAnalysisResults = async () => {
  return api.get("/analysisresults/");
};

// 数据可视化相关API
export const createVisualization = async (
  dataFileId,
  analysisResultId,
  chartType,
  title,
  configuration
) => {
  return api.post("/visualizations/visualize/", {
    data_file_id: dataFileId,
    analysis_result_id: analysisResultId,
    chart_type: chartType,
    title,
    configuration,
  });
};

export const getVisualizations = async () => {
  return api.get("/visualizations/");
};

// 数据导出 - 实际上是直接下载文件
export const exportData = async (fileId, format = "csv") => {
  return api.get(`/datafiles/${fileId}/export/`, {
    params: { format },
    responseType: "blob",
  });
};

export default api;

# Infrastructure

基础设施目录保存与运行环境相关、可版本化的配置：

- `docker/`：前端和后端镜像定义；
- `nginx/`：静态资源和 API 反向代理配置；
- `compose.yaml`：本地或演示环境服务编排；
- `deployment/`：后续部署平台配置。

密钥和生产参数不得写入本目录，应由部署环境注入。


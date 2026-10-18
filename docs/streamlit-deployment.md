# Streamlit 部署与模型配置

仓库使用 `main` 分支，应用入口为 `ui/app.py`，Python 版本为 3.11。部署后首次启动会从 `knowledge/seed.zip` 恢复 17 个来源、4,235 个文本块；原始材料和未入库候选的边界见 `knowledge/README.md`。

## 切换到 DeepSeek V4 Pro

在 Streamlit Community Cloud 的应用 Settings → Secrets 中保留现有内容，在末尾添加以下独立配置节。如果已经存在 `[aeroregqa_llm]`，请修改原节，不要重复添加。

```toml
[aeroregqa_llm]
LLM_API_KEY = "填写自己的 DeepSeek API 密钥"
LLM_BASE_URL = "https://api.deepseek.com/v1"
LLM_MODEL_NAME = "deepseek-v4-pro"
LLM_JUDGE_MODEL_NAME = "deepseek-v4-pro"
LLM_LITE_MODEL_NAME = "deepseek-v4-pro"
LLM_REASONER_MODEL_NAME = "deepseek-v4-pro"
LLM_ROUTER_MODEL_NAME = "deepseek-v4-pro"
LLM_THINKING_MODE = "disabled"
```

保存后等待应用重新启动；若仍显示旧模型，在管理菜单中执行 Reboot。侧边栏“当前模型”和技术架构标签应显示 `deepseek-v4-pro`。该配置节优先于历史顶层 LLM 配置，不修改 Embedding 或其他服务设置。

`EMBEDDING_API_KEY` 仍需使用对应服务商的密钥，默认服务商为硅基流动，向量模型必须保持 `BAAI/bge-m3`。DeepSeek 的密钥不能代替硅基流动的密钥。已有向量与其他模型不兼容时需要重新建库。

DeepSeek 官方 V4 默认开启思考模式；应用显式使用 `disabled`，避免路由、改写、生成和评估各步骤都进入较长的思考过程。可改为 `enabled`，但响应时间和 token 使用量可能增加。该请求参数仅发给 `api.deepseek.com` 的受支持模型，不发送给其他兼容接口。

模型与接口说明：[模型列表](https://api-docs.deepseek.com/api/list-models/)、[思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)。

## 上线验证

1. 页面出现 17 个来源、4,235 个文本块；已有上传会使数量增加。
2. 当前模型显示 `deepseek-v4-pro`。
3. 提问“根据已收录文件，CCAR-92 的适用范围是什么？请标注原文来源”，确认有答案和可核查的来源。
4. 若模型调用失败，分别检查 LLM 与 Embedding 的服务商、密钥、余额和模型名，勿把密钥粘贴到 GitHub、日志或问题截图中。

网站是共享演示实例，访客上传和对话暂未隔离，云端运行目录重置后会丢失新增内容。公开发布代码并不证明云端 Secrets 已正确配置，线上测试需单独完成。

## 本地验证

```bash
python -m pytest -q
streamlit run ui/app.py
```

测试在临时目录恢复内置索引，不调用付费接口。`.env`、`.streamlit/secrets.toml` 和 `_maintenance/` 已被 Git 忽略。

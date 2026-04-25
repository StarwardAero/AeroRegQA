import streamlit as st


def render_thinking_status(agent_steps: list):
    """渲染 AI 思考的详细动画与日志"""
    if not agent_steps:
        return

    with st.status("正在分析问题并生成回答", expanded=True) as status:
        for step in agent_steps:
            if step.step_type == "rewrite":
                st.write(f"**问题理解**：将问题重写为 `{step.output_data}`（{step.duration_ms} ms）")
            elif step.step_type == "retrieve":
                sources = step.metadata.get("sources", [])
                st.write(
                    f"**知识检索**：找到相关资料 {step.output_data}。来源：{', '.join(sources)}（{step.duration_ms} ms）"
                )
            elif step.step_type == "generate":
                st.write(f"**草稿生成**：正在构建回答内容（{step.duration_ms} ms）")
            elif step.step_type == "judge":
                score_str = step.output_data.split(".")[0] if "." in step.output_data else step.output_data
                is_acc = "通过" if "True" in step.output_data else "未通过，继续优化"
                st.write(f"**结果评估**：{score_str}，{is_acc}（{step.duration_ms} ms）")
            elif step.step_type == "generate_final":
                st.write(f"**最终输出**：完成回答整理（{step.duration_ms} ms）")

        if agent_steps[-1].step_type == "generate_final" or (agent_steps[-1].step_type == "judge" and "True" in agent_steps[-1].output_data):
            status.update(label="分析完成，已生成最终回答", state="complete", expanded=False)
        else:
            status.update(label="继续检索更合适的依据与答案", state="running")

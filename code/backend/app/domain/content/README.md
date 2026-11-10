# Content

`curriculum.json` 为四个方向的课程、二十个单元题库和四份方向后测提供唯一内容源。
`catalog.py` 统一加载课程及 `learner/assessment_items.json` 的八题前测，提供公开内容、答案校验和版本化客观判分。
公开取题不含正确答案和解析；提交结果保存题目与反馈快照。
题目来源 ID 用于去重，语言维度与认知目标是待教学校验的初始标签。

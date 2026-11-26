# assessment

`LearningJourney.vue` 组合首页、前测、方向选择、单元学习、后测和画像页面，负责导航、焦点与伴学上下文。
`useLearningProgress.ts` 管理课程与进度加载、草稿保存队列、版本冲突、测验提交、重测和前测分析。
这些状态属于当前账号的组件实例；根组件通过用户 ID 的 `key` 在切换账号时重建，避免共享局部状态。

`ServerUnitQuiz.vue` 共用于前测、单元与后测。题目来自后端，正式分数和画像由后端生成；
已登录用户的草稿、提交和分析可在刷新后恢复。`LearningAnalysis.vue`、`LearnerProfile.vue` 和 `FinalReport.vue` 展示相应结果。
接口见 `shared/api/`，回归测试见 `tests/progress.test.ts`、`journey.test.ts` 和 `server-unit.test.ts`。
